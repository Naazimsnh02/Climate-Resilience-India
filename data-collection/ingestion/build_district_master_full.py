"""Expand district_master from the 23-district El Nino seed to all ~763 LGD districts.

Source of truth for the full district list: Ministry of Panchayati Raj's Local Government
Directory (LGD), mirrored as a clean CSV at
https://github.com/planemad/india-local-government-directory (administrative/2-district.csv),
snapshotted here as raw_cache/lgd_district_raw.csv. This is the current post-reorganization
list (e.g. already reflects Andhra Pradesh's 26-district split), not the 2011 Census's 640.

Lat/lon: the 23 seed districts keep their existing hand-checked centroids. The ~740 new
districts are geocoded via OpenStreetMap Nominatim (free, no key, 1 req/sec policy limit) --
slow (~15 min), so results are checkpointed to raw_cache/district_geocode_cache.csv one row
at a time and re-runs skip districts already resolved. Matches the "don't lose progress to a
premature kill" lesson from DATA_SOURCES.md/PROGRESS.md.

flagged_belt / primary_kharif_crops / datagovin_district_name are hand-researched fields that
only exist for the 23 seed districts; new districts get NULL/best-guess placeholders here --
filling those in for all ~763 is out of scope for this step (see PROGRESS.md "Full-India
scaling" plan, steps 3-5).
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import requests
from common.config import SEED_DIR, RAW_CACHE_DIR

LGD_CSV = RAW_CACHE_DIR / "lgd_district_raw.csv"
GEOCODE_CACHE = RAW_CACHE_DIR / "district_geocode_cache.csv"
OUT_CSV = SEED_DIR / "district_master.csv"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "climate-resilience-india-hackathon/1.0 (district centroid geocoding, one-time batch)"

STATE_ABBREV = {
    "ANDAMAN AND NICOBAR ISLANDS": "an", "ANDHRA PRADESH": "ap", "ARUNACHAL PRADESH": "ar",
    "ASSAM": "as", "BIHAR": "br", "CHANDIGARH": "ch", "CHHATTISGARH": "cg", "DELHI": "dl",
    "GOA": "ga", "GUJARAT": "gj", "HARYANA": "hr", "HIMACHAL PRADESH": "hp",
    "JAMMU AND KASHMIR": "jk", "JHARKHAND": "jh", "KARNATAKA": "ka", "KERALA": "kl",
    "LADAKH": "la", "LAKSHADWEEP": "ld", "MADHYA PRADESH": "mp", "MAHARASHTRA": "mh",
    "MANIPUR": "mn", "MEGHALAYA": "ml", "MIZORAM": "mz", "NAGALAND": "nl", "ODISHA": "od",
    "PUDUCHERRY": "py", "PUNJAB": "pb", "RAJASTHAN": "rj", "SIKKIM": "sk",
    "TAMIL NADU": "tn", "TELANGANA": "ts",
    "THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU": "dn", "TRIPURA": "tr",
    "UTTAR PRADESH": "up", "UTTARAKHAND": "uk", "WEST BENGAL": "wb",
}

# Renames/aliases so the 23 hand-curated seed rows match their LGD counterpart by name.
# This LGD snapshot still uses the pre-2023 Maharashtra names (Aurangabad/Osmanabad), not
# the seed's current official names -- same rename mismatch DATA_SOURCES.md already
# documented for the data.gov.in mandi/rainfall APIs.
NAME_ALIASES = {
    ("mh", "chhatrapati sambhajinagar"): "aurangabad",
    ("mh", "dharashiv (osmanabad)"): "osmanabad",
    ("gj", "kutch"): "kachchh",
}


def title_case(name: str) -> str:
    small = {"and", "of", "the"}
    words = name.strip().title().split(" ")
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        out.append(lw if lw in small and i != 0 else w)
    return " ".join(out)


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s


def norm(name: str) -> str:
    """Alnum-only key for matching seed<->LGD names across spacing variants
    (e.g. seed's "Banaskantha" vs LGD's "Banas Kantha") without needing a manual alias."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def load_lgd():
    df = pd.read_csv(LGD_CSV, encoding="utf-8-sig")
    df["state_abbrev"] = df["State Name"].map(STATE_ABBREV)
    missing = df[df["state_abbrev"].isna()]["State Name"].unique()
    if len(missing):
        raise ValueError(f"No abbreviation mapped for states: {missing}")
    df["name"] = df["District Name"].map(title_case)
    df["state"] = df["State Name"].map(title_case)
    df["name_slug"] = df["name"].map(slugify)
    df["name_norm"] = df["name"].map(norm)
    df["district_id"] = df["state_abbrev"] + "_" + df["name_slug"]
    # A handful of districts share a slug within a state after title-casing (rare); disambiguate.
    dupe_mask = df.duplicated("district_id", keep=False)
    if dupe_mask.any():
        df.loc[dupe_mask, "district_id"] = (
            df.loc[dupe_mask, "district_id"] + "_" + df.loc[dupe_mask, "Census 2011 Code"].astype(str)
        )
    return df


def load_seed():
    # Read from the frozen 23-district seed, never from OUT_CSV -- this script overwrites
    # OUT_CSV (district_master.csv) with its own output, so reading the seed from there
    # would feed a prior run's merged 763-row output back in as if it were the original
    # hand-curated seed, permanently losing the real seed's district_ids on every rerun.
    df = pd.read_csv(SEED_DIR / "district_master_seed23.csv")
    df["state_abbrev"] = df["district_id"].str.split("_").str[0]
    df["match_key"] = df.apply(
        lambda r: norm(NAME_ALIASES.get((r["state_abbrev"], r["name"].lower()), r["name"])),
        axis=1,
    )
    return df


def load_geocode_cache():
    if GEOCODE_CACHE.exists():
        return pd.read_csv(GEOCODE_CACHE, index_col="district_id")
    return pd.DataFrame(columns=["lat", "lon"]).rename_axis("district_id")


def geocode_one(name: str, state: str):
    params = {"format": "json", "q": f"{name} district, {state}, India", "limit": 1}
    resp = requests.get(
        NOMINATIM_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=15
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        # Fallback: drop "district" qualifier, some LGD names (e.g. city-districts) don't match it.
        params["q"] = f"{name}, {state}, India"
        resp = requests.get(
            NOMINATIM_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=15
        )
        resp.raise_for_status()
        results = resp.json()
    if not results:
        return None, None
    return float(results[0]["lat"]), float(results[0]["lon"])


def geocode_missing(lgd, cache):
    todo = lgd[~lgd["district_id"].isin(cache.index)]
    print(f"{len(todo)} districts need geocoding ({len(cache)} already cached)")
    rows = list(todo[["district_id", "name", "state"]].itertuples(index=False))
    for i, (district_id, name, state) in enumerate(rows):
        try:
            lat, lon = geocode_one(name, state)
        except requests.RequestException as e:
            print(f"  [{i+1}/{len(rows)}] {district_id}: request failed ({e}), will retry next run")
            continue
        status = "ok" if lat is not None else "NO MATCH"
        print(f"  [{i+1}/{len(rows)}] {district_id}: {status} ({lat}, {lon})")
        with open(GEOCODE_CACHE, "a", encoding="utf-8") as f:
            if f.tell() == 0:
                f.write("district_id,lat,lon\n")
            f.write(f"{district_id},{lat if lat is not None else ''},{lon if lon is not None else ''}\n")
        time.sleep(1.1)


def main():
    lgd = load_lgd()
    seed = load_seed()

    cache = load_geocode_cache()
    geocode_missing(lgd, cache)
    cache = load_geocode_cache()

    merged = lgd.merge(
        seed[["district_id", "name", "match_key", "state_abbrev", "flagged_belt", "primary_kharif_crops",
              "datagovin_district_name", "lat", "lon"]],
        left_on=["name_norm", "state_abbrev"],
        right_on=["match_key", "state_abbrev"],
        how="left",
        suffixes=("", "_seed"),
    )
    # Every downstream BigQuery table (mandi_prices, ndvi_soil_moisture, crop_advisory,
    # reservoir_status, rag_corpus, etc.) is keyed on the seed's original district_id --
    # a matched seed row MUST keep it, never the freshly-generated LGD-derived one, or
    # every existing row for that district silently becomes unjoinable. Same for the
    # display name: the seed's curated name (e.g. "Chhatrapati Sambhajinagar", "Kutch")
    # reflects deliberate hand-research, not this LGD snapshot's sometimes-stale spelling
    # (e.g. "Aurangabad", "Kachchh").
    merged["district_id"] = merged["district_id_seed"].fillna(merged["district_id"])
    merged["name"] = merged["name_seed"].fillna(merged["name"])
    merged = merged.merge(cache, on="district_id", how="left", suffixes=("", "_geo"))
    merged["lat"] = merged["lat"].fillna(merged["lat_geo"])
    merged["lon"] = merged["lon"].fillna(merged["lon_geo"])
    merged["datagovin_district_name"] = merged["datagovin_district_name"].fillna(merged["name"])

    unresolved = merged[merged["lat"].isna()]
    if len(unresolved):
        print(f"WARNING: {len(unresolved)} districts still have no lat/lon (geocode had no match):")
        print(unresolved[["district_id", "name", "state"]].to_string(index=False))

    out = merged[[
        "district_id", "name", "state", "lat", "lon", "flagged_belt",
        "primary_kharif_crops", "datagovin_district_name",
    ]].sort_values(["state", "name"])

    out.to_csv(OUT_CSV, index=False)
    print(f"Wrote {len(out)} districts to {OUT_CSV} ({out['flagged_belt'].notna().sum()} carry seed enrichment)")


if __name__ == "__main__":
    main()
