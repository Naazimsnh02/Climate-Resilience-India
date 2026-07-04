"""Central config loader. Reads .env from the repo root, not from data-collection/."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

DATA_GOV_IN_KEY = os.environ["DATA_GOV_IN"]
DATA_GOV_IN_NEW_KEY = os.environ["DATA_GOV_IN_NEW"]
OPENWEATHERMAP_API_KEY = os.environ["OPENWEATHERMAP_API_KEY"]
GCP_PROJECT = os.environ["GCP_PROJECT"]
BQ_DATASET = os.environ["BQ_DATASET"]
GCS_BUCKET = os.environ["GCS_BUCKET"]

RAW_CACHE_DIR = Path(__file__).resolve().parents[1] / "raw_cache"
SEED_DIR = Path(__file__).resolve().parents[1] / "seed"
