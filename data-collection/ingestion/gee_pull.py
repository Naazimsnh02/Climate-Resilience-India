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
from common.config import GCP_PROJECT, BQ_DATASET, SEED_DIR
from common.bq_loader import load_dataframe, client

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


def already_pulled_today(end_date):
    """district_ids already loaded for today's pulled_at date, so a rerun after this
    environment kills the background job (observed repeatedly at 763-district scale)
    resumes instead of re-running (and re-appending duplicate rows for) every district
    already done."""
    table_id = f"{GCP_PROJECT}.{BQ_DATASET}.ndvi_soil_moisture"
    try:
        rows = client().query(
            f"SELECT DISTINCT district_id FROM `{table_id}` WHERE pulled_at = '{end_date.date().isoformat()}'"
        ).result()
        return {r.district_id for r in rows}
    except Exception:
        return set()


def main():
    districts = pd.read_csv(SEED_DIR / "district_master.csv")
    ee.Initialize(project=GCP_PROJECT)
    end_date = datetime.now(timezone.utc)

    done = already_pulled_today(end_date)
    todo = districts[~districts["district_id"].isin(done)]
    print(f"{len(done)} districts already pulled today, {len(todo)} to go")

    # At 763-district scale a single batch-at-the-end load risks losing the whole run to
    # a rate limit, a transient GEE error, or this environment's habit of killing
    # long-lived background bash jobs after a few minutes - load each district straight
    # to BigQuery as it's pulled instead (same fix already applied to mgnrega_employment.py).
    pulled = 0
    for _, d in todo.iterrows():
        print(f"Pulling GEE data for {d['district_id']}...")
        try:
            vals = pull_for_district(d["district_id"], d["lat"], d["lon"], end_date)
        except Exception as exc:
            print(f"  FAILED: {exc}")
            continue
        ndvi_raw = vals.get("ndvi_raw")
        row = pd.DataFrame([{
            "district_id": d["district_id"],
            "pulled_at": end_date.date().isoformat(),
            "precip_mm_30d": vals.get("precip_mm_30d"),
            "precip_asof": vals.get("precip_asof"),
            "ndvi": (ndvi_raw * 0.0001) if ndvi_raw is not None else None,
            "ndvi_asof": vals.get("ndvi_asof"),
            "soil_moisture_pct": vals.get("soil_moisture_ssm"),
            "soil_moisture_asof": vals.get("soil_moisture_asof"),
            "source": "GEE:CHIRPS+MOD13Q1+SMAP10KM",
        }])
        load_dataframe(row, "ndvi_soil_moisture", write_disposition="WRITE_APPEND")
        pulled += 1

    print(f"Loaded {pulled}/{len(districts)} districts.")


if __name__ == "__main__":
    main()
