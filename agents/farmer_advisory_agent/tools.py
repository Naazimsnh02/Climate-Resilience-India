"""BigQuery-backed tools for the Farmer Advisory Agent (PLAN.md section 4).

Reuses `_resolve_district_id` and `get_risk_score` from the Triage Agent so both
agents agree on what "risk" means for a district - one model, multiple decision
surfaces, per PLAN.md section 4's design intent.
"""
from google.cloud import bigquery

from agents.common.bq_client import client
from agents.common.config import GCP_PROJECT, BQ_DATASET
from agents.triage_agent.tools import _resolve_district_id, get_risk_score  # noqa: F401 (re-exported)

T = f"{GCP_PROJECT}.{BQ_DATASET}"


def get_rainfall_forecast(district_id: str) -> dict:
    """Gets the 5-day rainfall forecast for a district, from OpenWeatherMap's free
    forecast API (data-collection/ingestion/weather_forecast.py) - the only genuinely
    forward-looking rainfall signal in this system. (CHIRPS/GEE precipitation data used
    elsewhere is a ~1-month-lagged satellite estimate of the past, not a forecast - don't
    confuse the two.)

    Args:
        district_id: Canonical district_id (e.g. "mh_latur") or a plain district name (e.g. "Latur").

    Returns:
        A dict with district_id, name, a "daily_forecast" list (each entry: forecast_date,
        expected_rain_mm, max_precip_probability), pulled_at timestamp, and source. Returns
        {"error": ...} if the district isn't found or has no forecast pulled yet.
    """
    resolved_id = _resolve_district_id(district_id)
    if resolved_id is None:
        return {"error": f"No district found matching '{district_id}'."}

    query = f"""
        SELECT m.district_id, m.name, w.forecast_date, w.expected_rain_mm,
               w.max_precip_probability, w.pulled_at, w.source
        FROM `{T}.district_master` m
        JOIN `{T}.weather_forecast` w ON w.district_id = m.district_id
        WHERE m.district_id = @district_id
        ORDER BY w.forecast_date
    """
    job = client().query(
        query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("district_id", "STRING", resolved_id)]
        ),
    )
    rows = list(job.result())
    if not rows:
        return {"error": f"No rainfall forecast pulled yet for '{resolved_id}'. Run weather_forecast.py."}

    return {
        "district_id": rows[0].district_id,
        "name": rows[0].name,
        "source": rows[0].source,
        "pulled_at": rows[0].pulled_at.isoformat() if hasattr(rows[0].pulled_at, "isoformat") else str(rows[0].pulled_at),
        "daily_forecast": [
            {
                "forecast_date": r.forecast_date.isoformat() if hasattr(r.forecast_date, "isoformat") else str(r.forecast_date),
                "expected_rain_mm": r.expected_rain_mm,
                "max_precip_probability": r.max_precip_probability,
            }
            for r in rows
        ],
    }


def get_crop_advisory(district_id: str) -> dict:
    """Gets crop-switch/sowing-window advisory rules for a district's kharif crops.

    Sourced via Gemini + Google Search grounding, one call per district
    (data-collection/ingestion/generate_crop_advisory.py), standing in for a full Vertex
    AI Search RAG corpus until real ICAR/state agri-dept advisory PDFs are collected and
    indexed. Every rule's `verified_grounded` flag tells you whether its source_url was
    confirmed against the actual search results Gemini grounded on, or is a fallback/
    unverified citation - treat unverified rules with lower confidence.

    Args:
        district_id: Canonical district_id (e.g. "mh_latur") or a plain district name (e.g. "Latur").

    Returns:
        A dict with district_id, name, primary_kharif_crops, and an "advisory_rules" list,
        each with crop, risk_condition, recommendation, rationale, source_url, and
        verified_grounded. Returns {"error": ...} if the district isn't found or has no
        advisory rules generated yet.
    """
    resolved_id = _resolve_district_id(district_id)
    if resolved_id is None:
        return {"error": f"No district found matching '{district_id}'."}

    query = f"""
        SELECT m.district_id, m.name, m.primary_kharif_crops,
               a.crop, a.risk_condition, a.recommendation, a.rationale,
               a.source_url, a.verified_grounded
        FROM `{T}.district_master` m
        LEFT JOIN `{T}.crop_advisory` a ON a.district_id = m.district_id
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
    if rows[0].crop is None:
        return {"error": f"No crop advisory generated yet for '{rows[0].name}'. Run generate_crop_advisory.py."}

    return {
        "district_id": rows[0].district_id,
        "name": rows[0].name,
        "primary_kharif_crops": rows[0].primary_kharif_crops,
        "advisory_rules": [
            {
                "crop": r.crop,
                "risk_condition": r.risk_condition,
                "recommendation": r.recommendation,
                "rationale": r.rationale,
                "source_url": r.source_url,
                "verified_grounded": r.verified_grounded,
            }
            for r in rows
        ],
    }
