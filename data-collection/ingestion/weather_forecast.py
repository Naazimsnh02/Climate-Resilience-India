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
from common.config import OPENWEATHERMAP_API_KEY, SEED_DIR
from common.bq_loader import load_dataframe

BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"


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


def main():
    districts = pd.read_csv(SEED_DIR / "district_master.csv")
    now = datetime.now(timezone.utc)

    rows = []
    for _, d in districts.iterrows():
        try:
            data = fetch(d["lat"], d["lon"])
        except Exception as exc:
            print(f"FAILED for {d['district_id']}: {exc}")
            continue
        daily = to_daily_buckets(data.get("list", []))
        for date, bucket in sorted(daily.items()):
            rows.append({
                "district_id": d["district_id"],
                "forecast_date": date,
                "pulled_at": now.isoformat(),
                "expected_rain_mm": round(bucket["rain_mm"], 2),
                "max_precip_probability": round(bucket["pop_max"], 2),
                "source": "OpenWeatherMap 5day/3hour forecast",
            })

    df = pd.DataFrame(rows)
    if df.empty:
        print("No rows pulled, skipping BigQuery load.")
        return
    # WRITE_TRUNCATE: this is a rolling forecast snapshot, not a time series of past
    # forecasts - each run replaces the prior forecast entirely, same rationale as
    # load_tier2_seed.py's static-snapshot tables.
    load_dataframe(df, "weather_forecast", write_disposition="WRITE_TRUNCATE")


if __name__ == "__main__":
    main()
