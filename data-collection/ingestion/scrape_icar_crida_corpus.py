"""Scrapes the ICAR-CRIDA District Agriculture Contingency Plan index
(icar-crida.res.in/CP-2012/district.html) to widen the RAG corpus from the 23
hand-matched seed districts to every district_master row the index covers.

The 2011-12 index page lists ~390 district PDFs grouped under <h3> state headers
(state names sometimes stale/misspelled: "Maharastra", "Orissa", "Rajastan",
"Tamilnadu" -- normalized against district_master's state names below). Districts
already in rag_corpus_manifest.csv (the 23 seed districts, matched by hand, some
already upgraded to newer /CP/<State>/ revisions) are left untouched -- this script
only adds NEW districts, never overwrites an existing manifest row.

Unmatched districts (no reasonable name match in the index) are left out --
generate_crop_advisory.py's Gemini+grounding fallback still covers those, per
the agreed full-India RAG plan in PROGRESS.md.

Resumable: downloads/uploads/manifest rows are appended one district at a time,
skipping district_ids already present in the manifest, so a killed run loses
no completed work (same lesson as mgnrega_employment.py / build_district_master_full.py).
"""
import difflib
import html
import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import requests
from google.cloud import storage
from common.config import SEED_DIR, RAW_CACHE_DIR, GCS_BUCKET

INDEX_URL = "https://www.icar-crida.res.in/CP-2012/district.html"
INDEX_HTML = RAW_CACHE_DIR / "icar_crida_cp2012_index.html"
BASE_URL = "https://www.icar-crida.res.in/CP-2012/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
GCS_PREFIX = "rag-corpus"
DOC_TYPE = "icar_contingency_plan_2012_index"

STATE_ALIASES = {
    "maharastra": "maharashtra",
    "orissa": "odisha",
    "rajastan": "rajasthan",
    "tamilnadu": "tamil nadu",
    "andhra pradesh": "andhra pradesh",
    "chattisgarh": "chhattisgarh",
}

# This 2011-12 index predates the 2014 Telangana bifurcation: its "Andhra Pradesh" section
# lists districts that are now in Telangana. Fall back to Telangana if a district isn't
# found under Andhra Pradesh in the current district_master.
STATE_FALLBACKS = {
    "andhra pradesh": "telangana",
}

H3_RE = re.compile(r'<h3[^>]*>.*?<font[^>]*>([^<]+)</font>.*?</h3>', re.IGNORECASE | re.DOTALL)
A_RE = re.compile(r'<a href="([^"]+)"[^>]*>([^<]*)</a>', re.IGNORECASE)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def fetch_index():
    if INDEX_HTML.exists():
        return INDEX_HTML.read_text(encoding="utf-8", errors="ignore")
    resp = requests.get(INDEX_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    INDEX_HTML.write_text(resp.text, encoding="utf-8")
    return resp.text


def parse_index(index_html: str):
    """Returns list of (state_name_raw, district_name_raw, pdf_url)."""
    # Split on <h3> blocks: each block is "state header + everything until next state header".
    parts = re.split(r'(?=<h3)', index_html)
    out = []
    for part in parts:
        h3_match = H3_RE.search(part)
        if not h3_match:
            continue
        state_raw = h3_match.group(1).strip()
        for href, text in A_RE.findall(part):
            name = html.unescape(text.strip())
            href = html.unescape(href)
            if not name or not href.lower().endswith(".pdf"):
                continue
            out.append((state_raw, name, urljoin(BASE_URL, href)))
    return out


def build_state_lookup(district_master: pd.DataFrame):
    """state_norm -> canonical state name in district_master."""
    lookup = {}
    for s in district_master["state"].unique():
        lookup[norm(s)] = s
    return lookup


def _match_in_state(district_raw, candidates):
    target = norm(district_raw)
    for _, row in candidates.iterrows():
        if norm(row["name"]) == target:
            return row["district_id"]

    close = difflib.get_close_matches(
        target, {norm(n): n for n in candidates["name"]}.keys(), n=1, cutoff=0.8
    )
    if close:
        matched_name = {norm(n): n for n in candidates["name"]}[close[0]]
        return candidates[candidates["name"] == matched_name].iloc[0]["district_id"]
    return None


def match_district(state_raw, district_raw, district_master, state_lookup):
    state_norm_key = state_raw.strip().lower()
    state_key = norm(STATE_ALIASES.get(state_norm_key, state_norm_key))
    canonical_state = state_lookup.get(state_key)
    if canonical_state is None:
        return None

    candidates = district_master[district_master["state"] == canonical_state]
    result = _match_in_state(district_raw, candidates)
    if result is not None:
        return result

    fallback_state_raw = STATE_FALLBACKS.get(state_norm_key)
    if fallback_state_raw:
        fallback_canonical = state_lookup.get(norm(fallback_state_raw))
        if fallback_canonical is not None:
            fallback_candidates = district_master[district_master["state"] == fallback_canonical]
            return _match_in_state(district_raw, fallback_candidates)
    return None


def main():
    district_master = pd.read_csv(SEED_DIR / "district_master.csv")
    manifest = pd.read_csv(SEED_DIR / "rag_corpus_manifest.csv")
    already_have = set(manifest["district_id"])

    index_html = fetch_index()
    entries = parse_index(index_html)
    print(f"Parsed {len(entries)} district PDF links from the index")

    state_lookup = build_state_lookup(district_master)

    matched, unmatched, skipped = [], [], []
    for state_raw, district_raw, pdf_url in entries:
        district_id = match_district(state_raw, district_raw, district_master, state_lookup)
        if district_id is None:
            unmatched.append((state_raw, district_raw))
            continue
        if district_id in already_have:
            skipped.append(district_id)
            continue
        matched.append((district_id, district_raw, pdf_url))

    print(f"{len(matched)} new districts matched, {len(skipped)} already in manifest, "
          f"{len(unmatched)} unmatched (state/name not in the index or no district_master match)")

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    ok = 0
    for i, (district_id, district_raw, pdf_url) in enumerate(matched):
        filename = Path(pdf_url.split("/")[-1].split("?")[0])
        blob_path = f"{GCS_PREFIX}/{district_id}/{filename}"
        try:
            resp = requests.get(pdf_url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            if not resp.content.startswith(b"%PDF"):
                raise ValueError("response is not a PDF")
            bucket.blob(blob_path).upload_from_string(resp.content, content_type="application/pdf")
            with open(SEED_DIR / "rag_corpus_manifest.csv", "a", encoding="utf-8", newline="") as f:
                f.write(f'{district_id},{DOC_TYPE},"{pdf_url}",district,{date.today().isoformat()}\n')
            print(f"  [{i+1}/{len(matched)}] OK   {district_id:25s} ({district_raw})")
            ok += 1
        except Exception as e:
            print(f"  [{i+1}/{len(matched)}] FAIL {district_id:25s} ({district_raw}) -> {e}")
        time.sleep(0.5)

    print(f"\n{ok}/{len(matched)} new district PDFs uploaded to gs://{GCS_BUCKET}/{GCS_PREFIX}/")
    if unmatched:
        print(f"\n{len(unmatched)} unmatched entries (first 20):")
        for state_raw, district_raw in unmatched[:20]:
            print(f"  {state_raw} / {district_raw}")


if __name__ == "__main__":
    main()
