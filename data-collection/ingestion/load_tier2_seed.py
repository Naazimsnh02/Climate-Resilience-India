"""Loads the hand-researched Tier 2 snapshot (reservoir/groundwater/drought) into BigQuery.

These sources (CWC reservoir bulletin, CGWB groundwater, NRSC drought bulletins) are
portal/PDF/bulletin-based, not REST APIs, so this is a manually-researched snapshot with
citations rather than a live puller. Reload this script whenever the snapshot is refreshed.
Uses WRITE_TRUNCATE since each run replaces the whole snapshot, not appends to a time series.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from common.config import SEED_DIR
from common.bq_loader import load_dataframe

TABLES = {
    "reservoir_status": "reservoir_status.csv",
    "groundwater_level": "groundwater_level.csv",
    "drought_status": "drought_status.csv",
}


def main():
    for table_name, filename in TABLES.items():
        df = pd.read_csv(SEED_DIR / filename)
        load_dataframe(df, table_name, write_disposition="WRITE_TRUNCATE")


if __name__ == "__main__":
    main()
