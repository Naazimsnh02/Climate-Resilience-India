# Progress Log — El Niño 2026 Decision Copilot

Snapshot of what's built, what works, and what's next. See `PLAN.md` for the full build plan
and long-term roadmap, `DATA_SOURCES.md` for data source findings/caveats.

## Status as of 2026-07-03

### Done

**Infra**
- GCP project `climate-resilience-in` created, billing linked, BigQuery dataset `raw_data` + GCS bucket live.

**Data ingestion (`data-collection/`)**
- 23 seed districts loaded in `district_master`, spanning the flagged El Niño belt (Marathwada–north
  Karnataka, Rajasthan, Gujarat, MP, Chhattisgarh, eastern UP, Bihar, Jharkhand).
- Tier 1 (live) sources wired and confirmed working end-to-end into BigQuery:
  - Google Earth Engine — CHIRPS precipitation, MODIS NDVI, SMAP soil moisture (`gee_pull.py` → `ndvi_soil_moisture`)
  - Agmarknet/data.gov.in mandi prices (`mandi_prices.py` → `mandi_prices`)
  - OpenWeatherMap current weather (`weather_current.py` → `weather_current`)
  - data.gov.in district rainfall (`rainfall_datagovin.py` → `rainfall_daily`) — historical/cross-check role only, not current-conditions (see `DATA_SOURCES.md`)
- Tier 2 (bulletin/portal, not REST) pre-seeded as a static snapshot, hand-researched with citations:
  - CWC reservoir status, CGWB groundwater trend, NRSC drought bulletin status (`load_tier2_seed.py` → `reservoir_status`, `groundwater_level`, `drought_status`)
- IMD direct rainfall API dropped — no self-serve key, not viable on a hackathon timeline.
- Known gaps recorded in `DATA_SOURCES.md`: data.gov.in 10-record page cap, non-exact filters, rate limiting, stale/deprecated datasets caught before they poisoned the model (SMAP10KM), district rename mismatches (Aurangabad/Chhatrapati Sambhajinagar etc).

**Risk model (`data-collection/modeling/build_risk_model.py`)**
- `district_features_latest` view — joins latest snapshot per district across all Tier 1 + Tier 2 sources.
- `district_risk_model` — BigQuery ML linear regression, trained to reproduce an ordinal (1-4) parsed from
  `drought_status.status` text, from live/seeded feature signals (precip, NDVI, soil moisture, reservoir %,
  groundwater trend, heat).
- `district_risk_score` table populated via `ML.EXPLAIN_PREDICT` — `risk_score` (0-100), `days_to_critical_reservoir`
  (heuristic), `rainfall_deficit_rank`, and per-district top feature attributions for explainability.
- Explicitly documented limitation: n=23 with no held-out split means this is a calibrated composite index,
  not a validated predictive model yet. See `PLAN.md` §8 for the path to real predictive ML.
- Sanity-checked: Marathwada cluster (Hingoli, Jalna, Dharashiv) tops the ranking, consistent with their
  "severe"/"high" drought bulletin status.

**Triage Agent (`agents/triage_agent/`)**
- Built on ADK + Gemini 2.5 Flash.
- Tools: `get_risk_score(district_id)` (accepts canonical id or plain district name, resolved via
  `district_master`) and `list_top_risk_districts(limit)`, both reading `district_risk_score` joined
  against `district_features_latest`.
- Verified end-to-end with a live Gemini call via `GOOGLE_API_KEY` — correctly calls `get_risk_score`,
  cites reservoir/groundwater/soil-moisture drivers, and states the drought bulletin status.
- Not yet built: `query_bigquery(sql)` (raw passthrough tool), `get_historical_analog(district_id)`.

### Not started
- Allocation Agent, Farmer Advisory Agent (PLAN.md §4)
- RAG corpus (crop advisory PDFs, MGNREGA guidelines, drought playbooks) + Vertex AI Search index
- Backend API (Cloud Run)
- Frontend (admin console map/drill-down, farmer chat UI, Looker Studio embed)
- Cloud Translation / localization
- Cloud Functions / Scheduler automation for recurring ingestion (all pulls currently run manually via `data-collection/run_all.py`)

## Next up
1. `get_historical_analog(district_id)` tool for the Triage Agent (PLAN.md §4)
2. Allocation Agent — constraint-aware tanker/budget allocation, reusing `district_risk_score`
3. Backend API (Cloud Run) to expose agent + risk endpoints to a frontend
