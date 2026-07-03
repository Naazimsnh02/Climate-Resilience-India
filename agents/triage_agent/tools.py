"""BigQuery-backed tools for the Triage Agent, reading from `district_risk_score`
(see data-collection/modeling/build_risk_model.py for how that table is built).
"""
import json

from google.cloud import bigquery

from agents.common.bq_client import client
from agents.common.config import GCP_PROJECT, BQ_DATASET

T = f"{GCP_PROJECT}.{BQ_DATASET}"

# One row per (district_id, date); always read the latest date so a rerun of
# build_risk_model.py is picked up without any tool-side caching to invalidate.
LATEST_SCORE_CTE = f"""
WITH latest AS (
  SELECT *
  FROM `{T}.district_risk_score`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY district_id ORDER BY date DESC) = 1
)
"""


def _resolve_district_id(district_id_or_name: str) -> str | None:
    """Accepts either a canonical district_id (e.g. 'mh_latur') or a free-text
    district name (e.g. 'Latur') and resolves it to a canonical district_id."""
    query = f"""
        SELECT district_id FROM `{T}.district_master`
        WHERE LOWER(district_id) = LOWER(@q) OR LOWER(name) = LOWER(@q)
        LIMIT 1
    """
    job = client().query(
        query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("q", "STRING", district_id_or_name)]
        ),
    )
    rows = list(job.result())
    return rows[0].district_id if rows else None


def get_risk_score(district_id: str) -> dict:
    """Gets the current El Nino 2026 drought/monsoon risk score and its explanation for one district.

    Args:
        district_id: Canonical district_id (e.g. "mh_latur") or a plain district name (e.g. "Latur").

    Returns:
        A dict with the district's risk_score (0-100, higher = more at-risk), the drought
        bulletin status behind it, days_to_critical_reservoir, rainfall_deficit_rank among
        seeded districts, top feature attributions driving the score (for explainability),
        model_version, and the score date. Returns {"error": ...} if the district isn't found
        or has no score yet.
    """
    resolved_id = _resolve_district_id(district_id)
    if resolved_id is None:
        return {"error": f"No district found matching '{district_id}'."}

    query = f"""
        {LATEST_SCORE_CTE}
        SELECT
          m.district_id, m.name, m.state, m.flagged_belt,
          l.date, l.risk_score, l.days_to_critical_reservoir, l.rainfall_deficit_rank,
          l.model_version, l.explanation_json,
          f.drought_status, f.reservoir_pct_full, f.groundwater_trend,
          f.precip_mm_30d, f.ndvi, f.soil_moisture_pct
        FROM latest l
        JOIN `{T}.district_master` m ON m.district_id = l.district_id
        LEFT JOIN `{T}.district_features_latest` f ON f.district_id = l.district_id
        WHERE l.district_id = @district_id
    """
    job = client().query(
        query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("district_id", "STRING", resolved_id)]
        ),
    )
    rows = list(job.result())
    if not rows:
        return {"error": f"District '{resolved_id}' has no risk score yet. Run build_risk_model.py."}

    r = rows[0]
    return {
        "district_id": r.district_id,
        "name": r.name,
        "state": r.state,
        "flagged_belt": r.flagged_belt,
        "date": r.date.isoformat(),
        "risk_score": r.risk_score,
        "days_to_critical_reservoir": r.days_to_critical_reservoir,
        "rainfall_deficit_rank": r.rainfall_deficit_rank,
        "drought_bulletin_status": r.drought_status,
        "reservoir_pct_full": r.reservoir_pct_full,
        "groundwater_trend": r.groundwater_trend,
        "precip_mm_30d": r.precip_mm_30d,
        "ndvi": r.ndvi,
        "soil_moisture_pct": r.soil_moisture_pct,
        "top_feature_attributions": json.loads(r.explanation_json) if r.explanation_json else [],
        "model_version": r.model_version,
    }


def get_historical_analog(district_id: str) -> dict:
    """Gets past notable drought years for a district, for historical-analog framing
    (e.g. "this district's current risk profile resembles its 2015-16 drought").

    Sourced from WebSearch research with citations (CWC/CGWB/NRSC portals aren't
    scrapable - see DATA_SOURCES.md), not a live feed. Some rows are `regional`
    granularity (nearest district/division-wide figure) rather than district-exact;
    always surface `granularity` alongside the years, same convention as reservoir/
    groundwater data.

    Args:
        district_id: Canonical district_id (e.g. "mh_latur") or a plain district name (e.g. "Latur").

    Returns:
        A dict with district_id, name, historical_drought_years (list of year/year-range
        strings, most recent first), granularity ("district" or "regional"), notes, and
        source_url. Returns {"error": ...} if the district isn't found or has no historical
        record seeded yet.
    """
    resolved_id = _resolve_district_id(district_id)
    if resolved_id is None:
        return {"error": f"No district found matching '{district_id}'."}

    query = f"""
        SELECT m.district_id, m.name, h.historical_drought_years, h.granularity,
               h.notes, h.source_url
        FROM `{T}.district_master` m
        LEFT JOIN `{T}.historical_drought_years` h ON h.district_id = m.district_id
        WHERE m.district_id = @district_id
    """
    job = client().query(
        query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("district_id", "STRING", resolved_id)]
        ),
    )
    rows = list(job.result())
    if not rows:
        return {"error": f"District '{resolved_id}' not found."}

    r = rows[0]
    if not r.historical_drought_years:
        return {"error": f"No historical drought-year record seeded yet for '{r.name}'."}

    years = r.historical_drought_years.split(";")
    return {
        "district_id": r.district_id,
        "name": r.name,
        "historical_drought_years": list(reversed(years)),
        "granularity": r.granularity,
        "notes": r.notes,
        "source_url": r.source_url,
    }


def list_top_risk_districts(limit: int = 20) -> dict:
    """Lists the districts with the highest current El Nino 2026 drought/monsoon risk score.

    Args:
        limit: Max number of districts to return, ranked highest-risk first (default 20, capped at 23
            since only 23 seed districts are currently tracked).

    Returns:
        A dict with a "districts" list, each entry containing district_id, name, state,
        flagged_belt, risk_score, and drought_bulletin_status.
    """
    limit = max(1, min(limit, 23))
    query = f"""
        {LATEST_SCORE_CTE}
        SELECT m.district_id, m.name, m.state, m.flagged_belt, l.risk_score, f.drought_status
        FROM latest l
        JOIN `{T}.district_master` m ON m.district_id = l.district_id
        LEFT JOIN `{T}.district_features_latest` f ON f.district_id = l.district_id
        ORDER BY l.risk_score DESC
        LIMIT {limit}
    """
    rows = list(client().query(query).result())
    return {
        "districts": [
            {
                "district_id": r.district_id,
                "name": r.name,
                "state": r.state,
                "flagged_belt": r.flagged_belt,
                "risk_score": r.risk_score,
                "drought_bulletin_status": r.drought_status,
            }
            for r in rows
        ]
    }
