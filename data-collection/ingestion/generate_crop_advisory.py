"""Generates crop-switch/sowing-window advisory rules for the Farmer Advisory Agent
(PLAN.md section 4) via Gemini + Google Search grounding, one call per seed district -
NOT hand-research, NOT a Claude-driven WebSearch loop, specifically to keep this data-
generation step cheap and repeatable (it can be rerun as new advisories are published).

This stands in for a full Vertex AI Search RAG corpus (PLAN.md's original design) until
real ICAR/state agri-dept advisory PDFs are collected and indexed - see PROGRESS.md for
that decision. Same pragmatic "seed a real, cited snapshot table" pattern as
load_tier2_seed.py / load_historical_drought_years.py, just generated via LLM+search
instead of manual research.

Accuracy safeguard: Gemini is asked to cite a source_url per rule, but models can still
fabricate a plausible-looking URL even when told to ground in search results. So every
claimed source_url is cross-checked against the *actual* URLs Google Search grounding
returned for that call (response.candidates[0].grounding_metadata.grounding_chunks) - if a
claimed URL isn't among the real grounded chunks, we replace it with the top grounded URL
for that response and mark verified_grounded=False so the gap is visible, rather than
silently trusting model-written text.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from google import genai
from google.genai import types

from common.config import SEED_DIR, GCP_PROJECT
from common.bq_loader import load_dataframe

MODEL = "gemini-2.5-flash"

PROMPT_TEMPLATE = """You are researching real, citable agricultural extension advice for
Indian farmers, using Google Search grounding. Do not invent information - only report
what your search results actually say.

District: {name}, {state}, India
Kharif crops grown here: {crops}
Context: 2026 El Nino monsoon season, IMD forecasting ~90-92% of normal rainfall, this
district is on the government's priority drought-watch list.

Search for real ICAR (Indian Council of Agricultural Research), ICAR-CRIDA district
agricultural contingency plan, or state agriculture department guidance for this district
or its agro-climatic region, covering what farmers should do if the monsoon is delayed or
deficient this kharif season - e.g. sowing window shifts, short-duration/drought-tolerant
variety substitution, or switching from a water-intensive crop (e.g. paddy) to a hardier
one (e.g. millet/pulses) under rainfall deficit.

Return ONLY a JSON array (no markdown fences, no commentary) of 1-3 objects, each with
exactly these fields:
  "crop": the crop this rule concerns (one of the kharif crops listed above, or "general")
  "risk_condition": the real-world trigger condition per your source, e.g. "monsoon onset
    delayed beyond 2-3 weeks" or "cumulative rainfall deficit exceeds 20% by mid-July"
  "recommendation": the concrete action recommended, in plain language
  "rationale": one sentence on why, per the source
  "source_url": the exact URL of the document/page you found this in

If you cannot find any district- or region-specific contingency guidance after
searching, return a single object with "crop": "general", "risk_condition": "no
district-specific contingency plan found", "recommendation": "consult the local Krishi
Vigyan Kendra or agriculture extension officer", "rationale": "no citable source found for
this district", "source_url": "".
"""


def _extract_grounded_urls(response) -> list[str]:
    urls = []
    try:
        candidate = response.candidates[0]
        chunks = candidate.grounding_metadata.grounding_chunks or []
        for chunk in chunks:
            if chunk.web and chunk.web.uri:
                urls.append(chunk.web.uri)
    except (AttributeError, IndexError, TypeError):
        pass
    return urls


def _parse_rules(text: str) -> list[dict]:
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        rules = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if not match:
            return []
        try:
            rules = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    return rules if isinstance(rules, list) else []


def generate_for_district(client, row) -> list[dict]:
    prompt = PROMPT_TEMPLATE.format(
        name=row["name"], state=row["state"], crops=row["primary_kharif_crops"]
    )
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.1,
        ),
    )
    grounded_urls = _extract_grounded_urls(response)
    rules = _parse_rules(response.text or "")

    out = []
    for rule in rules:
        source_url = (rule.get("source_url") or "").strip()
        verified = bool(source_url) and source_url in grounded_urls
        if source_url and not verified and grounded_urls:
            source_url = grounded_urls[0]
        out.append({
            "district_id": row["district_id"],
            "crop": rule.get("crop", "general"),
            "risk_condition": rule.get("risk_condition", ""),
            "recommendation": rule.get("recommendation", ""),
            "rationale": rule.get("rationale", ""),
            "source_url": source_url,
            "verified_grounded": verified,
        })
    return out


def main():
    # Vertex AI backend (billed against GCP_PROJECT, already linked) rather than the
    # Gemini Developer API key - the free API-key tier caps at 20 requests/day/model,
    # which isn't enough to cover 23 districts in one run (hit mid-run on 2026-07-03).
    client = genai.Client(vertexai=True, project=GCP_PROJECT, location="global")

    districts = pd.read_csv(SEED_DIR / "district_master.csv")

    only_missing = "--retry-missing" in sys.argv
    existing_path = SEED_DIR / "crop_advisory.csv"
    existing_df = pd.read_csv(existing_path) if (only_missing and existing_path.exists()) else None
    if existing_df is not None:
        done_ids = set(existing_df["district_id"].unique())
        districts = districts[~districts["district_id"].isin(done_ids)]
        print(f"--retry-missing: {len(done_ids)} districts already done, "
              f"{len(districts)} remaining.")

    all_rows = list(existing_df.to_dict("records")) if existing_df is not None else []
    for _, d in districts.iterrows():
        print(f"Generating advisory for {d['district_id']}...")
        try:
            rows = generate_for_district(client, d)
        except Exception as exc:
            print(f"  FAILED for {d['district_id']}: {exc}")
            continue
        print(f"  -> {len(rows)} rule(s), "
              f"{sum(r['verified_grounded'] for r in rows)} verified-grounded")
        all_rows.extend(rows)
        time.sleep(1)  # light pacing against rate limits

    df = pd.DataFrame(all_rows)
    out_path = SEED_DIR / "crop_advisory.csv"
    df.to_csv(out_path, index=False)
    print(f"\nWrote {len(df)} rows to {out_path}")

    load_dataframe(df, "crop_advisory", write_disposition="WRITE_TRUNCATE")


if __name__ == "__main__":
    main()
