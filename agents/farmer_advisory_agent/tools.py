"""BigQuery-backed tools for the Farmer Advisory Agent (PLAN.md section 4).

Reuses `_resolve_district_id` and `get_risk_score` from the Triage Agent so both
agents agree on what "risk" means for a district - one model, multiple decision
surfaces, per PLAN.md section 4's design intent.
"""
from google.cloud import bigquery
from google.cloud import discoveryengine_v1 as discoveryengine

from agents.common.bq_client import client
from agents.common.config import GCP_PROJECT, BQ_DATASET, VERTEX_SEARCH_LOCATION, VERTEX_SEARCH_ENGINE_ID
from agents.triage_agent.tools import _resolve_district_id, get_risk_score  # noqa: F401 (re-exported)

T = f"{GCP_PROJECT}.{BQ_DATASET}"

_search_client = None


def _get_search_client():
    global _search_client
    if _search_client is None:
        _search_client = discoveryengine.SearchServiceClient()
    return _search_client


def search_advisory_corpus(district_id: str, question: str) -> dict:
    """Searches the real ICAR-CRIDA District Agriculture Contingency Plan corpus
    (Vertex AI Search over actual government PDFs, see DATA_SOURCES.md and
    data-collection/seed/rag_corpus_manifest.csv) for guidance relevant to a farmer's
    question. This is real source-document retrieval - prefer it over `get_crop_advisory`
    (which is Gemini-generated text) whenever it returns a hit, since it lets you cite an
    actual contingency-plan passage rather than an LLM's paraphrase of one.

    Args:
        district_id: Canonical district_id (e.g. "mh_latur") or a plain district name (e.g. "Latur").
        question: The farmer's question or topic to search for (e.g. "delayed sowing soybean").

    Returns:
        A dict with district_id, name, and a "results" list of {snippet, document_title,
        document_uri}, each snippet a real passage from that district's ICAR contingency
        plan PDF. Returns {"error": ...} if the district isn't found, and an empty
        "results" list (not an error) if the corpus has no relevant passage - in that case
        fall back to `get_crop_advisory`.
    """
    resolved_id = _resolve_district_id(district_id)
    if resolved_id is None:
        return {"error": f"No district found matching '{district_id}'."}

    query = f"""
        SELECT name FROM `{T}.district_master` WHERE district_id = @district_id
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
    district_name = rows[0].name

    serving_config = (
        f"projects/{GCP_PROJECT}/locations/{VERTEX_SEARCH_LOCATION}/collections/default_collection/"
        f"engines/{VERTEX_SEARCH_ENGINE_ID}/servingConfigs/default_search"
    )
    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=f"{district_name} district: {question}",
        page_size=10,
        content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
            snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                return_snippet=True
            ),
        ),
    )
    response = _get_search_client().search(request)

    # The data store holds all 23 districts' PDFs; Discovery Engine has no
    # documented server-side filter for GCS folder path on a content store, so
    # scope to this district by checking the returned GCS URI contains its
    # rag-corpus/{district_id}/ prefix rather than trusting query relevance alone.
    results = []
    for result in response.results:
        derived = result.document.derived_struct_data
        link = derived.get("link") if derived else None
        if not link or f"rag-corpus/{resolved_id}/" not in link:
            continue
        title = derived.get("title") if derived else None
        for s in derived.get("snippets", []) if derived else []:
            snippet_text = s.get("snippet")
            if snippet_text:
                results.append(
                    {
                        "snippet": snippet_text,
                        "document_title": title,
                        "document_uri": link,
                    }
                )

    return {
        "district_id": resolved_id,
        "name": district_name,
        "results": results,
    }


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
