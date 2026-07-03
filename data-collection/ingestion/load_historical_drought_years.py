"""Loads the hand-researched historical drought-year snapshot into BigQuery, for the
Triage Agent's get_historical_analog tool. Same pattern as load_tier2_seed.py: this is
WebSearch-sourced with citations (CWC/CGWB/NRSC portals aren't scrapable, see
DATA_SOURCES.md), not a live puller. Uses WRITE_TRUNCATE - re-run after editing the seed CSV.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from common.config import SEED_DIR
from common.bq_loader import load_dataframe


def main():
    df = pd.read_csv(SEED_DIR / "historical_drought_years.csv")
    load_dataframe(df, "historical_drought_years", write_disposition="WRITE_TRUNCATE")


if __name__ == "__main__":
    main()
