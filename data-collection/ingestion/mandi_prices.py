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


def already_loaded_states():
    """States already loaded in this run/a prior run, so a rerun after a crash or a
    rate-limited state doesn't re-fetch (and re-append duplicate rows for) states
    that already succeeded."""
    from common.bq_loader import client
    from common.config import GCP_PROJECT, BQ_DATASET
    table_id = f"{GCP_PROJECT}.{BQ_DATASET}.mandi_prices"
    try:
        rows = client().query(f"SELECT DISTINCT State FROM `{table_id}`").result()
        return {r.State for r in rows}
    except Exception:
        return set()  # table doesn't exist yet on a first run


def main():
    districts = pd.read_csv(SEED_DIR / "district_master.csv")
    states = sorted(districts["state"].unique())
    done = already_loaded_states()
    todo = [s for s in states if s not in done]
    print(f"{len(done)} states already loaded, {len(todo)} to fetch")

    # Full-India scale (~36 states/UTs vs. the original 9) makes a single
    # batch-at-the-end load risky - a rate limit, a connection timeout, or a killed
    # background job partway through would lose every state already fetched. Load
    # per-state as we go instead (see DATA_SOURCES.md's flagged follow-up + the same
    # fix in mgnrega_employment.py), and catch broad request failures (not just 429s)
    # so one flaky state doesn't kill the whole run.
    loaded_states = 0
    for state in todo:
        print(f"Fetching mandi prices for {state}...")
        try:
            recs = fetch_state(state)
        except (RuntimeError, requests.exceptions.RequestException) as exc:
            print(f"  SKIPPED (request failure, rerun to retry): {exc}")
            continue
        print(f"  {len(recs)} records")
        if recs:
            df = pd.DataFrame(recs)
            df["pulled_at"] = datetime.now(timezone.utc).isoformat()
            load_dataframe(df, "mandi_prices", write_disposition="WRITE_APPEND")
            loaded_states += 1
        time.sleep(1)  # cool off between states, not just between pages

    print(f"Loaded mandi prices for {loaded_states}/{len(todo)} attempted states "
          f"({len(done) + loaded_states}/{len(states)} total).")


if __name__ == "__main__":
    main()
