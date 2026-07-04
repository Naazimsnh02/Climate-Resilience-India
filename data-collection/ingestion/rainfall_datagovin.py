"""Pulls district-level daily rainfall from data.gov.in ("Daily District-wise Rainfall
Data", NRSC VIC Model estimates via NWIC/Ministry of Jal Shakti).

Resource confirmed live 2026-07-03: filterable by State/District, fields are
State, District, Date, Year, Month, Avg_rainfall, Agency_name.

Important caveats found by live-testing, not assumed from docs:
  - Portal metadata says "Updated On 31/12/2025" but per-district data coverage is
    patchy - some districts stop well before that (e.g. Beed's most recent rows
    were June 2025 in one sample query), and volume is far short of a true daily
    series (a handful of hundred rows/year per district, not 365). Treat this as a
    slow-moving historical/backfill source, NOT a live feed - GEE's CHIRPS precip
    (gee_pull.py) is the live rainfall signal; this is a cross-check / longer
    baseline only.
  - District names in this dataset predate 2023 renames: use "Aurangabad" not
    "Chhatrapati Sambhajinagar", "Osmanabad" not "Dharashiv", "Kachchh" not "Kutch".
    See district_master.csv's `datagovin_district_name` column, which carries the
    name this API actually expects per district.
"""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
import pandas as pd
from common.config import DATA_GOV_IN_KEY, GCP_PROJECT, BQ_DATASET, SEED_DIR
from common.bq_loader import load_dataframe, client

RESOURCE_ID = "6c05cd1b-ed59-40c2-bc31-e314f39c6971"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
# api.data.gov.in silently stalls (read timeout) on requests' default User-Agent -
# see mandi_prices.py for the same fix.
HEADERS = {"User-Agent": "curl/8.4.0", "Accept": "*/*"}
RECORDS_PER_DISTRICT = 90  # most recent rows available, not necessarily most recent dates
# The API silently caps each response at 10 records regardless of the requested
# `limit` (confirmed live: limit=90 still returned count=10, response echoed
# limit=10) - pagination via offset is mandatory, not optional.
PAGE_SIZE = 10


def get_with_retry(url, params, max_attempts=9):
    for attempt in range(max_attempts):
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 429:
            # Backoff capped at 60s - the old uncapped 2**attempt with only 5 attempts (~31s
            # total) gave up before data.gov.in's throttling window cleared, permanently
            # skipping ~69 districts in one run (mgnrega_employment.py hit the same issue -
            # see its get_with_retry for the same fix).
            wait = min(2 ** attempt, 60)
            print(f"    rate limited, retrying in {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp
    raise RuntimeError(f"Gave up after {max_attempts} attempts (rate limited): {url}")


def fetch_district(state, district_name, max_records=RECORDS_PER_DISTRICT):
    records = []
    offset = 0
    while offset < max_records:
        resp = get_with_retry(
            BASE_URL,
            params={
                "api-key": DATA_GOV_IN_KEY,
                "format": "json",
                "limit": PAGE_SIZE,
                "offset": offset,
                "filters[State]": state,
                "filters[District]": district_name,
            },
        )
        batch = resp.json().get("records", [])
        if not batch:
            break
        records.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(0.3)
    return records


def already_pulled():
    """district_ids already loaded, so a rerun after this environment kills the
    background job resumes instead of re-fetching every district already done."""
    table_id = f"{GCP_PROJECT}.{BQ_DATASET}.rainfall_daily"
    try:
        rows = client().query(f"SELECT DISTINCT district_id FROM `{table_id}`").result()
        return {r.district_id for r in rows}
    except Exception:
        return set()


def main():
    districts = pd.read_csv(SEED_DIR / "district_master.csv")
    now = datetime.now(timezone.utc).isoformat()

    done = already_pulled()
    todo = districts[~districts["district_id"].isin(done)]
    print(f"{len(done)} districts already pulled, {len(todo)} to go")

    # Load per-district as we go, not one batch at the end - at 763-district scale a
    # data.gov.in rate limit or a killed background job shouldn't cost every district
    # already fetched (same fix as mandi_prices.py/gee_pull.py/weather_current.py).
    pulled = 0
    for _, d in todo.iterrows():
        lookup_name = d["datagovin_district_name"]
        print(f"Fetching rainfall for {d['district_id']} (as '{lookup_name}')...")
        try:
            recs = fetch_district(d["state"], lookup_name)
        except Exception as exc:
            print(f"  FAILED: {exc}")
            continue
        print(f"  {len(recs)} records")
        if recs:
            for r in recs:
                r["district_id"] = d["district_id"]
            df = pd.DataFrame(recs)
            df["pulled_at"] = now
            load_dataframe(df, "rainfall_daily", write_disposition="WRITE_APPEND")
            pulled += 1

    print(f"Loaded rainfall data for {pulled} districts this run "
          f"({len(done) + pulled}/{len(districts)} total).")


if __name__ == "__main__":
    main()
