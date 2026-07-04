"""Expands reservoir_status from the 23 hand-researched seed districts to every
district_master row, per the agreed "regional fallback by default" Tier 2 scope
(PROGRESS.md "Full-India scaling") -- hand-research doesn't scale to ~763 districts,
so every district without a real district-level row gets its state's CWC weekly
reservoir bulletin *regional* aggregate (Northern/Eastern/Western/Central/Southern,
see seed/cwc_regional_reservoir_fallback.csv, sourced 2026-06-25) instead of a null.

Only covers reservoir_status. groundwater_level (CGWB) and drought_status (NRSC) have
no equally clean regional-aggregate source found yet -- still seed-only (23 districts),
a known gap, not silently backfilled with guessed numbers.

States outside CWC's 5 monitored regions (Bihar, Haryana, all NE states, J&K/Ladakh,
Goa, Delhi and other UTs) get no fallback row at all, same as today -- no CWC regional
bulletin exists to source one honestly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from common.config import SEED_DIR


def main():
    district_master = pd.read_csv(SEED_DIR / "district_master.csv")
    hand = pd.read_csv(SEED_DIR / "reservoir_status.csv")
    fallback = pd.read_csv(SEED_DIR / "cwc_regional_reservoir_fallback.csv")

    state_fallback = fallback.set_index("state")

    hand_district_ids = set(hand["district_id"])
    new_rows = []
    for _, row in district_master.iterrows():
        if row["district_id"] in hand_district_ids:
            continue
        if row["state"] not in state_fallback.index:
            continue
        fb = state_fallback.loc[row["state"]]
        new_rows.append({
            "district_id": row["district_id"],
            "reservoir_name": None,
            "pct_full": fb["pct_full"],
            "pct_normal": None,
            "asof_date": fb["asof_date"],
            "granularity": "regional_fallback",
            "notes": fb["notes"],
            "source_url": fb["source_url"],
        })

    combined = pd.concat([hand, pd.DataFrame(new_rows)], ignore_index=True)
    combined.to_csv(SEED_DIR / "reservoir_status.csv", index=False)
    print(f"reservoir_status.csv: {len(hand)} hand-researched + {len(new_rows)} regional-fallback "
          f"= {len(combined)} rows ({len(district_master) - len(combined)} districts still with no "
          f"reservoir signal at all -- states outside CWC's 5 monitored regions)")


if __name__ == "__main__":
    main()
