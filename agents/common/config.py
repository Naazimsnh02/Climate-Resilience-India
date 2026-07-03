"""Central config loader for the agents package. Reads .env from the repo root."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

GCP_PROJECT = os.environ["GCP_PROJECT"]
BQ_DATASET = os.environ["BQ_DATASET"]

# Vertex AI Search (Discovery Engine) - real ICAR-CRIDA district contingency plan
# corpus, see data-collection/seed/rag_corpus_manifest.csv and PLAN.md section 4/6.
VERTEX_SEARCH_LOCATION = "global"
VERTEX_SEARCH_ENGINE_ID = "crop-advisory-search"
