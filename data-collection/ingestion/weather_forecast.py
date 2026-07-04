"""Pulls a 5-day/3-hour rainfall forecast per seed district from OpenWeatherMap's free
`/forecast` endpoint (same API key as weather_current.py). This is the only genuinely
forward-looking rainfall signal in the pipeline - CHIRPS (gee_pull.py) is a ~1-month-lagged
satellite estimate of the past, not a forecast. Aggregates the 3-hour steps into daily
buckets: total expected rain (mm) and max precipitation probability (pop), for the
Farmer Advisory Agent's "should I sow this week" use case.
"""
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
import pandas as pd
from common.config import GCP_PROJECT, BQ_DATASET, OPENWEATHERMAP_API_KEY, SEED_DIR
from common.bq_loader import load_dataframe, client

BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"
RESUME_WINDOW = "INTERVAL 2 HOUR"  # treat rows pulled within this window as "this run"


def fetch(lat, lon):
    resp = requests.get(
        BASE_URL,
        params={"lat": lat, "lon": lon, "appid": OPENWEATHERMAP_API_KEY, "units": "metric"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def to_daily_buckets(forecast_list):
    """Groups 3-hour steps by calendar date (UTC), summing rain and taking max pop."""
    daily = defaultdict(lambda: {"rain_mm": 0.0, "pop_max": 0.0, "steps": 0})
    for step in forecast_list:
        date = datetime.fromtimestamp(step["dt"], tz=timezone.utc).date().isoformat()
        bucket = daily[date]
        bucket["rain_mm"] += step.get("rain", {}).get("3h", 0.0)
        bucket["pop_max"] = max(bucket["pop_max"], step.get("pop", 0.0))
        bucket["steps"] += 1
    return daily


def already_pulled_this_run():
    """district_ids already loaded within the last couple hours, so a rerun after this
    environment kills the background job resumes the same rolling-snapshot run instead
    of re-truncating and re-fetching every district already done."""
    table_id = f"{GCP_PROJECT}.{BQ_DATASET}.weather_forecast"
    try:
        rows = client().query(
            f"SELECT DISTINCT district_id FROM `{table_id}` "
            f"WHERE pulled_at > CAST((CURRENT_TIMESTAMP() - {RESUME_WINDOW}) AS STRING)"
        ).result()
        return {r.district_id for r in rows}
    except Exception:
        return set()


def main():
    districts = pd.read_csv(SEED_DIR / "district_master.csv")
    now = datetime.now(timezone.utc)

    done = already_pulled_this_run()
    todo = districts[~districts["district_id"].isin(done)]
    print(f"{len(done)} districts already pulled this run, {len(todo)} to go")

    # Load per-district as we go, not one batch at the end, so a failure partway through
    # 763 districts leaves a valid (partial) snapshot instead of losing the whole run
    # (same fix as gee_pull.py/mandi_prices.py/weather_current.py). The first district
    # of a fresh run still replaces the prior snapshot (WRITE_TRUNCATE); every district
    # after that - including on a resumed run - appends, preserving the "rolling
    # snapshot, not a time series" semantics.
    pulled = 0
    is_fresh_run = len(done) == 0
    for _, d in todo.iterrows():
        try:
            data = fetch(d["lat"], d["lon"])
        except Exception as exc:
            print(f"FAILED for {d['district_id']}: {exc}")
            continue
        daily = to_daily_buckets(data.get("list", []))
        rows = [
            {
                "district_id": d["district_id"],
                "forecast_date": date,
                "pulled_at": now.isoformat(),
                "expected_rain_mm": round(bucket["rain_mm"], 2),
                "max_precip_probability": round(bucket["pop_max"], 2),
                "source": "OpenWeatherMap 5day/3hour forecast",
            }
            for date, bucket in sorted(daily.items())
        ]
        if rows:
            write_disposition = "WRITE_TRUNCATE" if (is_fresh_run and pulled == 0) else "WRITE_APPEND"
            load_dataframe(pd.DataFrame(rows), "weather_forecast", write_disposition=write_disposition)
            pulled += 1

    print(f"Loaded {pulled} districts this run ({len(done) + pulled}/{len(districts)} total).")


if __name__ == "__main__":
    main()
