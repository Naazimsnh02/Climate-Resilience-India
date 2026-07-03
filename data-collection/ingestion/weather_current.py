"""Pulls current weather (temperature, humidity -> heatwave/wet-bulb stress signal)
per seed district from OpenWeatherMap, using district centroid lat/lon.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
import pandas as pd
from common.config import OPENWEATHERMAP_API_KEY, SEED_DIR
from common.bq_loader import load_dataframe

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def fetch(lat, lon):
    resp = requests.get(
        BASE_URL,
        params={"lat": lat, "lon": lon, "appid": OPENWEATHERMAP_API_KEY, "units": "metric"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


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
        main_data = data.get("main", {})
        rows.append(
            {
                "district_id": d["district_id"],
                "timestamp": now.isoformat(),
                "temp_c": main_data.get("temp"),
                "feels_like_c": main_data.get("feels_like"),
                "humidity_pct": main_data.get("humidity"),
                "weather_main": (data.get("weather") or [{}])[0].get("main"),
                "weather_desc": (data.get("weather") or [{}])[0].get("description"),
                "source": "OpenWeatherMap",
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        print("No rows pulled, skipping BigQuery load.")
        return
    load_dataframe(df, "weather_current", write_disposition="WRITE_APPEND")


if __name__ == "__main__":
    main()
