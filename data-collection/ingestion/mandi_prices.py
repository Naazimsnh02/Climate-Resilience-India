"""Pulls daily mandi (market) prices from data.gov.in for the states our seed districts cover.
Resource confirmed live 2026-07-03: "Current Daily Price of Various Commodities from Various
Markets (Mandi)", updated daily by Ministry of Agriculture and Farmers Welfare.
"""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
import pandas as pd
from common.config import DATA_GOV_IN_KEY, SEED_DIR
from common.bq_loader import load_dataframe

RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
# api.data.gov.in silently caps every response at 10 records regardless of the
# requested `limit` (confirmed live: limit=1000 still returned count=10, response
# echoed limit=10) - the old `len(batch) < PAGE_SIZE` loop-exit check never fired
# because batch was always exactly 10, so this was silently truncating every
# state to its first 10 records. PAGE_SIZE now matches the real server cap so the
# exit check is meaningful again.
PAGE_SIZE = 10
# api.data.gov.in silently stalls (read timeout, no error) on requests' default
# User-Agent - some WAF rule. A curl-like UA fixes it. Found by comparing curl
# (instant) vs. requests (hung every time) against the identical URL.
HEADERS = {"User-Agent": "curl/8.4.0", "Accept": "*/*"}


def get_with_retry(url, params, max_attempts=5):
    for attempt in range(max_attempts):
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 429:
            wait = 2 ** attempt
            print(f"    rate limited, retrying in {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp
    raise RuntimeError(f"Gave up after {max_attempts} attempts (rate limited): {url}")


def fetch_state(state, max_records=5000):
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
                "filters[state]": state,
            },
        )
        batch = resp.json().get("records", [])
        if not batch:
            break
        records.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(0.6)  # be polite between pages, avoid re-triggering 429
    return records


def main():
    districts = pd.read_csv(SEED_DIR / "district_master.csv")
    states = sorted(districts["state"].unique())

    all_records = []
    for state in states:
        print(f"Fetching mandi prices for {state}...")
        try:
            recs = fetch_state(state)
        except RuntimeError as exc:
            print(f"  SKIPPED (rate limited past retry budget): {exc}")
            continue
        print(f"  {len(recs)} records")
        all_records.extend(recs)
        time.sleep(1)  # cool off between states, not just between pages

    if not all_records:
        print("No records fetched, skipping BigQuery load.")
        return

    df = pd.DataFrame(all_records)
    df["pulled_at"] = datetime.now(timezone.utc).isoformat()
    load_dataframe(df, "mandi_prices", write_disposition="WRITE_APPEND")


if __name__ == "__main__":
    main()
