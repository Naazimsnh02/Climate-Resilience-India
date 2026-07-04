"""Pulls district-wise MGNREGA employment data from data.gov.in for the states our seed
districts cover. Intended as the future risk-model label: person-days actually worked is an
independent, behavioral signal of rural distress (households falling back on guaranteed work),
unlike drought_status.status which is scraped bulletin text derived from the same rainfall/NDVI
features already in the model. See docs/PLAN.md section 8 and docs/DATA_SOURCES.md.

Resource confirmed live 2026-07-03: "District-wise MGNREGA Data at a Glance"
(Ministry of Rural Development / Dept of Land Resources), updated daily, monthly-cadence rows,
415,834 total records nationwide as of this pull. No direct "person-days demanded" field -
Persondays_of_Central_Liability_so_far (cumulative work provided) and Total_Households_Worked
are the closest proxies; deriving a month-over-month/anomaly-vs-prior-year signal from these is
a modeling step for later, not this ingestion script.

Rate-limit strategy: data.gov.in throttles aggressively, so each (state, fin_year) combination
is treated as one "attempt" with exactly 60s between attempts (regardless of success, failure,
or skip) - e.g. Bihar 2024-2025, wait 60s, Bihar 2025-2026, wait 60s, etc. Pagination *within*
one attempt still uses a short 0.6s inter-page sleep since that's a different rate-limit context.
A JSON checkpoint file tracks completed combinations so a killed/interrupted run can be safely
re-invoked and will only fetch what's still missing.
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
import pandas as pd
from common.config import DATA_GOV_IN_NEW_KEY, SEED_DIR, RAW_CACHE_DIR, BQ_DATASET
from common.bq_loader import load_dataframe, client

RESOURCE_ID = "ee03643a-ee4c-48c2-ac30-9f2ff26ab722"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
TABLE_NAME = "mgnrega_employment"
# Same undocumented 10-record server-side cap and WAF/User-Agent quirk already found for the
# mandi-prices and rainfall data.gov.in resources (see DATA_SOURCES.md) - confirmed to also
# apply here (limit=1000 still echoed back limit=10 on a live test call).
PAGE_SIZE = 10
HEADERS = {"User-Agent": "curl/8.4.0", "Accept": "*/*"}
# This resource is a monthly time series back to at least fin_year 2023-2024. Bound to the last
# few financial years, which is what a demand-anomaly-vs-prior-year label needs anyway.
FIN_YEARS = ["2024-2025", "2025-2026", "2026-2027"]

# An earlier run capped pagination at max_records=2000 per (state, fin_year), which silently
# truncated any state with more than 2000 monthly/district rows in a fin_year (Gujarat, Jharkhand,
# Karnataka, Madhya Pradesh, Maharashtra, Rajasthan all hit this exactly at 2000 rows). There is no
# real cap in the data - keep a very high ceiling only as a runaway-loop guard, not a real limit.
MAX_RECORDS_GUARD = 200_000
# Threshold used to detect rows loaded by that old buggy run: any (state, fin_year) already in BQ
# with a row count >= this is presumed truncated and gets deleted + re-fetched from scratch.
TRUNCATION_THRESHOLD = 2000

CHECKPOINT_FILE = RAW_CACHE_DIR / "mgnrega_checkpoint.json"

ATTEMPT_GAP_SECONDS = 60


def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        return json.loads(CHECKPOINT_FILE.read_text())
    return {}


def save_checkpoint(checkpoint):
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_FILE.write_text(json.dumps(checkpoint, indent=2, sort_keys=True))


def key(state, fin_year):
    return f"{state.upper()}|{fin_year}"


def get_bq_row_counts():
    """Returns {(state_name, fin_year): row_count} for whatever is already loaded in BQ."""
    query = f"""
        SELECT state_name, fin_year, COUNT(*) AS n
        FROM `{client().project}.{BQ_DATASET}.{TABLE_NAME}`
        GROUP BY state_name, fin_year
    """
    try:
        rows = client().query(query).result()
        return {(r.state_name, r.fin_year): r.n for r in rows}
    except Exception as exc:
        print(f"  (no existing table or query failed, assuming empty: {exc})", flush=True)
        return {}


def delete_truncated_rows(state, fin_year):
    table_id = f"{client().project}.{BQ_DATASET}.{TABLE_NAME}"
    query = f"""
        DELETE FROM `{table_id}`
        WHERE UPPER(state_name) = @state AND fin_year = @fin_year
    """
    from google.cloud import bigquery
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("state", "STRING", state.upper()),
            bigquery.ScalarQueryParameter("fin_year", "STRING", fin_year),
        ]
    )
    client().query(query, job_config=job_config).result()
    print(f"  Deleted truncated rows for {state} {fin_year}", flush=True)


def get_with_retry(url, params, max_attempts=9):
    for attempt in range(max_attempts):
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 429:
            # Backoff capped at 60s - uncapped 2**attempt would hit ~4min on the last attempt
            # alone. Total wait across all 9 attempts is ~4min, enough to survive whatever
            # throttling window data.gov.in enforces (observed to outlast the old 31s budget).
            wait = min(2 ** attempt, 60)
            print(f"    rate limited, retrying in {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp
    raise RuntimeError(f"Gave up after {max_attempts} attempts (rate limited): {url}")


def fetch_state_year(state, fin_year, max_records=MAX_RECORDS_GUARD):
    records = []
    offset = 0
    while offset < max_records:
        resp = get_with_retry(
            BASE_URL,
            params={
                "api-key": DATA_GOV_IN_NEW_KEY,
                "format": "json",
                "limit": PAGE_SIZE,
                "offset": offset,
                "filters[state_name]": state.upper(),
                "filters[fin_year]": fin_year,
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
    if offset >= max_records:
        print(f"  WARNING: hit runaway guard of {max_records} records for {state} {fin_year}", flush=True)
    return records


def main():
    districts = pd.read_csv(SEED_DIR / "district_master.csv")
    states = sorted(districts["state"].unique())
    # Optional: python mgnrega_employment.py "Gujarat,Jharkhand" - restrict this run to specific
    # states (still respects the checkpoint/BQ reconciliation for what's already complete).
    if len(sys.argv) > 1:
        wanted = {s.strip().upper() for s in sys.argv[1].split(",")}
        states = [s for s in states if s.upper() in wanted]

    checkpoint = load_checkpoint()
    bq_counts = get_bq_row_counts()

    # Reconcile: anything in BQ at/above the old truncation threshold is presumed incomplete from
    # the earlier capped run - delete it and clear its checkpoint entry so it gets re-fetched.
    for (bq_state, bq_fin_year), count in bq_counts.items():
        k = key(bq_state, bq_fin_year)
        if count >= TRUNCATION_THRESHOLD:
            print(f"{bq_state} {bq_fin_year}: {count} rows in BQ >= truncation threshold, will re-fetch", flush=True)
            delete_truncated_rows(bq_state, bq_fin_year)
            checkpoint.pop(k, None)
        elif checkpoint.get(k, {}).get("status") != "complete":
            # Already loaded fully by BQ's account, but checkpoint didn't know - record it.
            checkpoint[k] = {"status": "complete", "row_count": count}
    save_checkpoint(checkpoint)

    for state in states:
        for fin_year in FIN_YEARS:
            k = key(state, fin_year)
            if checkpoint.get(k, {}).get("status") == "complete":
                print(f"{state} {fin_year}: already complete, skipping", flush=True)
                continue

            print(f"Fetching MGNREGA employment data for {state} ({fin_year})...", flush=True)
            try:
                recs = fetch_state_year(state, fin_year)
            except RuntimeError as exc:
                print(f"  SKIPPED (rate limited past retry budget): {exc}", flush=True)
                time.sleep(ATTEMPT_GAP_SECONDS)
                continue

            # filters[state_name]/[fin_year] on this API are analyzed/fuzzy like the other
            # data.gov.in resources (DATA_SOURCES.md) - re-filter client-side rather than trust it.
            recs = [
                r for r in recs
                if r.get("state_name", "").strip().upper() == state.upper()
                and r.get("fin_year", "").strip() == fin_year
            ]
            print(f"  {len(recs)} records", flush=True)

            if recs:
                df = pd.DataFrame(recs)
                df["pulled_at"] = datetime.now(timezone.utc).isoformat()
                load_dataframe(df, TABLE_NAME, write_disposition="WRITE_APPEND")

            checkpoint[k] = {"status": "complete", "row_count": len(recs)}
            save_checkpoint(checkpoint)

            time.sleep(ATTEMPT_GAP_SECONDS)


if __name__ == "__main__":
    main()
