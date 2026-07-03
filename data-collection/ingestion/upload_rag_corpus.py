"""Downloads real ICAR-CRIDA District Agriculture Contingency Plan PDFs (one per seed
district, see seed/rag_corpus_manifest.csv - every URL confirmed reachable by live
WebSearch/WebFetch research 2026-07-03, not guessed) and stages them in GCS under
rag-corpus/{district_id}/ so a Vertex AI Search data store can be pointed at the
prefix. This replaces the Gemini+Search-generated crop_advisory table as the
long-term RAG source (see PLAN.md section 4/6) - crop_advisory stays as the fallback
for districts/questions the corpus doesn't cover.
"""
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
import pandas as pd
from google.cloud import storage
from common.config import GCS_BUCKET, SEED_DIR

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
GCS_PREFIX = "rag-corpus"


def main():
    manifest = pd.read_csv(SEED_DIR / "rag_corpus_manifest.csv")
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)

    ok, failed = [], []
    for row in manifest.itertuples():
        district_id = row.district_id
        url = row.source_url
        filename = Path(urlparse(url).path).name
        blob_path = f"{GCS_PREFIX}/{district_id}/{filename}"

        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            if resp.headers.get("Content-Type", "").lower().find("pdf") == -1 and not resp.content.startswith(b"%PDF"):
                raise ValueError(f"response is not a PDF (content-type={resp.headers.get('Content-Type')})")

            blob = bucket.blob(blob_path)
            blob.upload_from_string(resp.content, content_type="application/pdf")
            print(f"OK   {district_id:20s} -> gs://{GCS_BUCKET}/{blob_path} ({len(resp.content)/1024:.0f} KB)")
            ok.append(district_id)
        except Exception as e:
            print(f"FAIL {district_id:20s} {url} -> {e}")
            failed.append(district_id)

    print(f"\n{len(ok)}/{len(manifest)} uploaded. Failed: {failed if failed else 'none'}")


if __name__ == "__main__":
    main()
