"""Read-only district risk endpoints backing the admin console map + drill-down
(PLAN.md section 1.1). Thin wrappers over the same BigQuery tables the Triage
Agent's tools read - see agents/triage_agent/tools.py for the query patterns
this mirrors (kept as plain SQL here rather than reusing the agent tools directly,
since these are non-agentic reads that don't need a Gemini round-trip).
"""
import json

from fastapi import APIRouter, HTTPException
from google.cloud import bigquery

from agents.common.bq_client import client
from agents.common.config import GCP_PROJECT, BQ_DATASET

router = APIRouter(prefix="/api/districts", tags=["districts"])

T = f"{GCP_PROJECT}.{BQ_DATASET}"

LATEST_SCORE_CTE = f"""
WITH latest AS (
  SELECT *
  FROM `{T}.district_risk_score`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY district_id ORDER BY date DESC) = 1
)
"""


@router.get("")
def list_districts():
    """All seeded districts with their latest risk score and map coordinates,
    for the admin console's district-risk choropleth/marker map."""
    query = f"""
        {LATEST_SCORE_CTE}
        SELECT m.district_id, m.name, m.state, m.lat, m.lon, m.flagged_belt,
               l.risk_score, l.date, f.drought_status
        FROM `{T}.district_master` m
        LEFT JOIN latest l ON l.district_id = m.district_id
        LEFT JOIN `{T}.district_features_latest` f ON f.district_id = m.district_id
        ORDER BY l.risk_score DESC NULLS LAST
    """
    rows = list(client().query(query).result())
    return {
        "districts": [
            {
                "district_id": r.district_id,
                "name": r.name,
                "state": r.state,
                "lat": r.lat,
                "lon": r.lon,
                "flagged_belt": r.flagged_belt,
                "risk_score": r.risk_score,
                "date": r.date.isoformat() if r.date else None,
                "drought_bulletin_status": r.drought_status,
            }
            for r in rows
        ]
    }


@router.get("/{district_id}")
def get_district(district_id: str):
    """Full drill-down detail for one district: risk score, explanation
    attributions, and every underlying signal (rainfall, reservoir, groundwater,
    NDVI/soil moisture, drought bulletin) with as-of timestamps, per the
    explainability/provenance requirement in PLAN.md section 5."""
    query = f"""
        {LATEST_SCORE_CTE}
        SELECT
          m.district_id, m.name, m.state, m.lat, m.lon, m.flagged_belt, m.primary_kharif_crops,
          l.date, l.risk_score, l.days_to_critical_reservoir, l.rainfall_deficit_rank,
          l.model_version, l.explanation_json,
          f.drought_status, f.drought_asof,
          f.reservoir_pct_full, f.reservoir_pct_normal, f.reservoir_asof, f.reservoir_granularity,
          f.groundwater_trend, f.groundwater_level_m_bgl, f.groundwater_asof,
          f.precip_mm_30d, f.precip_asof, f.ndvi, f.ndvi_asof,
          f.soil_moisture_pct, f.soil_moisture_asof,
          f.temp_c, f.feels_like_c, f.humidity_pct, f.weather_asof
        FROM `{T}.district_master` m
        LEFT JOIN latest l ON l.district_id = m.district_id
        LEFT JOIN `{T}.district_features_latest` f ON f.district_id = m.district_id
        WHERE m.district_id = @district_id OR LOWER(m.name) = LOWER(@district_id)
    """
    job = client().query(
        query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("district_id", "STRING", district_id)]
        ),
    )
    rows = list(job.result())
    if not rows:
        raise HTTPException(status_code=404, detail=f"District '{district_id}' not found.")

    r = rows[0]
    return {
        "district_id": r.district_id,
        "name": r.name,
        "state": r.state,
        "lat": r.lat,
        "lon": r.lon,
        "flagged_belt": r.flagged_belt,
        "primary_kharif_crops": r.primary_kharif_crops,
        "risk": {
            "date": r.date.isoformat() if r.date else None,
            "risk_score": r.risk_score,
            "days_to_critical_reservoir": r.days_to_critical_reservoir,
            "rainfall_deficit_rank": r.rainfall_deficit_rank,
            "model_version": r.model_version,
            "top_feature_attributions": json.loads(r.explanation_json) if r.explanation_json else [],
        },
        "signals": {
            # All *_asof fields are plain STRING columns already (pulled_at/as-of stamps
            # written by the ingestion scripts, not BigQuery DATE/TIMESTAMP types).
            "drought_bulletin_status": {"value": r.drought_status, "as_of": r.drought_asof},
            "reservoir_pct_full": {"value": r.reservoir_pct_full, "pct_of_10yr_normal": r.reservoir_pct_normal, "as_of": r.reservoir_asof, "granularity": r.reservoir_granularity},
            "groundwater_trend": {"value": r.groundwater_trend, "level_m_bgl": r.groundwater_level_m_bgl, "as_of": r.groundwater_asof},
            "precip_mm_30d": {"value": r.precip_mm_30d, "as_of": r.precip_asof},
            "ndvi": {"value": r.ndvi, "as_of": r.ndvi_asof},
            "soil_moisture_pct": {"value": r.soil_moisture_pct, "as_of": r.soil_moisture_asof},
            "weather": {"temp_c": r.temp_c, "feels_like_c": r.feels_like_c, "humidity_pct": r.humidity_pct, "as_of": r.weather_asof},
        },
    }
