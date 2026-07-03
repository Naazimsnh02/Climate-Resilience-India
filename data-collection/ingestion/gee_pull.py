"""Pulls district-level satellite signals from Google Earth Engine:
  - CHIRPS daily precipitation (sum over trailing window) -> rainfall proxy
  - MODIS NDVI (latest 16-day composite) -> vegetation/crop stress
  - NASA-USDA SMAP soil moisture (latest) -> drought signal

Writes one row per district to BigQuery table `ndvi_soil_moisture`.
Run after load_district_master.py.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ee
import pandas as pd
from common.config import GCP_PROJECT, SEED_DIR
from common.bq_loader import load_dataframe

PRECIP_WINDOW_DAYS = 30


def district_region(lat, lon, buffer_m=15000):
    return ee.Geometry.Point([lon, lat]).buffer(buffer_m)


def pull_for_district(district_id, lat, lon, end_date):
    region = district_region(lat, lon)

    # CHIRPS finalized daily data lags real time by weeks-to-months, so a fixed
    # "last 30 days from now" window is often empty. Anchor on the latest image
    # actually present in the collection instead of the wall-clock date.
    chirps_coll = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").select("precipitation")
    latest_chirps = chirps_coll.sort("system:time_start", False).first()
    latest_chirps_date = ee.Date(latest_chirps.get("system:time_start"))
    chirps_window = chirps_coll.filterDate(
        latest_chirps_date.advance(-PRECIP_WINDOW_DAYS, "day"), latest_chirps_date.advance(1, "day")
    ).sum()
    precip_val = chirps_window.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=region, scale=5000, maxPixels=1e9
    ).get("precipitation")
    precip_asof = latest_chirps_date.format("YYYY-MM-dd")

    # Same latency issue applies to MODIS and SMAP - sort the whole collection by
    # time and take the latest image actually present, don't assume "now" is covered.
    ndvi_img = (
        ee.ImageCollection("MODIS/061/MOD13Q1")
        .select("NDVI")
        .sort("system:time_start", False)
        .first()
    )
    ndvi_val = ee.Algorithms.If(
        ndvi_img,
        ee.Image(ndvi_img)
        .reduceRegion(reducer=ee.Reducer.mean(), geometry=region, scale=250, maxPixels=1e9)
        .get("NDVI"),
        None,
    )
    ndvi_asof = ee.Algorithms.If(
        ndvi_img, ee.Date(ee.Image(ndvi_img).get("system:time_start")).format("YYYY-MM-dd"), None
    )

    # NASA_USDA/HSL/SMAP10KM_soil_moisture is deprecated and stalled in Aug 2022 -
    # verified live 2026-07-03 (returns 2022-08-02 as its latest image). Using the
    # successor collection instead, confirmed current as of 2026-06-30.
    smap_img = (
        ee.ImageCollection("NASA/SMAP/SPL4SMGP/008")
        .select("sm_surface")
        .sort("system:time_start", False)
        .first()
    )
    smap_val = ee.Algorithms.If(
        smap_img,
        ee.Image(smap_img)
        .reduceRegion(reducer=ee.Reducer.mean(), geometry=region, scale=10000, maxPixels=1e9)
        .get("sm_surface"),
        None,
    )
    smap_asof = ee.Algorithms.If(
        smap_img, ee.Date(ee.Image(smap_img).get("system:time_start")).format("YYYY-MM-dd"), None
    )

    result = ee.Dictionary(
        {
            "precip_mm_30d": precip_val,
            "precip_asof": precip_asof,
            "ndvi_raw": ndvi_val,
            "ndvi_asof": ndvi_asof,
            "soil_moisture_ssm": smap_val,
            "soil_moisture_asof": smap_asof,
        }
    ).getInfo()
    return result


def main():
    districts = pd.read_csv(SEED_DIR / "district_master.csv")
    ee.Initialize(project=GCP_PROJECT)
    end_date = datetime.now(timezone.utc)

    rows = []
    for _, d in districts.iterrows():
        print(f"Pulling GEE data for {d['district_id']}...")
        try:
            vals = pull_for_district(d["district_id"], d["lat"], d["lon"], end_date)
        except Exception as exc:
            print(f"  FAILED: {exc}")
            continue
        ndvi_raw = vals.get("ndvi_raw")
        rows.append(
            {
                "district_id": d["district_id"],
                "pulled_at": end_date.date().isoformat(),
                "precip_mm_30d": vals.get("precip_mm_30d"),
                "precip_asof": vals.get("precip_asof"),
                "ndvi": (ndvi_raw * 0.0001) if ndvi_raw is not None else None,
                "ndvi_asof": vals.get("ndvi_asof"),
                "soil_moisture_pct": vals.get("soil_moisture_ssm"),
                "soil_moisture_asof": vals.get("soil_moisture_asof"),
                "source": "GEE:CHIRPS+MOD13Q1+SMAP10KM",
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        print("No rows pulled, skipping BigQuery load.")
        return
    load_dataframe(df, "ndvi_soil_moisture", write_disposition="WRITE_APPEND")


if __name__ == "__main__":
    main()
