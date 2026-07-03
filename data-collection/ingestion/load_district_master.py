"""One-time (or idempotent re-run) loader: seed/district_master.csv -> BigQuery district_master table.

Note: lat/lon in the seed CSV are approximate district-centroid coordinates, good enough
for satellite region queries (GEE) at district granularity. Replace with LGD/Census
shapefile centroids before anything that needs precise boundaries.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from common.config import SEED_DIR
from common.bq_loader import load_dataframe


def main():
    df = pd.read_csv(SEED_DIR / "district_master.csv")
    load_dataframe(df, "district_master", write_disposition="WRITE_TRUNCATE")


if __name__ == "__main__":
    main()
