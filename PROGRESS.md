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
- Tools: `get_risk_score(district_id)`, `list_top_risk_districts(limit)`, and
  `get_historical_analog(district_id)` (accepts canonical id or plain district name, resolved via
  `district_master`), reading `district_risk_score`/`district_features_latest` and the new
  `historical_drought_years` table.
- Verified end-to-end with a live Gemini call via `GOOGLE_API_KEY` — correctly calls `get_risk_score`,
  cites reservoir/groundwater/soil-moisture drivers, and states the drought bulletin status.
- Not yet built: `query_bigquery(sql)` (raw passthrough tool).

**Historical drought years (`historical_drought_years` table, 2026-07-03)**
- WebSearch-researched, citation-backed CSV (`data-collection/seed/historical_drought_years.csv`,
  loaded via `load_historical_drought_years.py`, `WRITE_TRUNCATE`) — real past drought years per
  seed district (e.g. Marathwada 2012-13/2014-15/2015-16/2018-19, Rajasthan chronic recurrence,
  Bundelkhand 2004-08/2015-16), not fabricated. Same `granularity` convention as Tier 2
  (district vs. regional) — several districts (Kalaburagi, Vijayapura, Bidar, Chitrakoot, Banda)
  only have region-wide sourcing, not district-exact years.

**Allocation Agent (`agents/allocation_agent/`)**
- Built on ADK + Gemini 2.5 Flash. Tool: `allocate_resources(total_units, resource_name,
  scope_state, scope_belt, district_ids)`.
- Deterministic (non-LLM) allocation algorithm so it's auditable: proportional to risk_score,
  discounted 0.6x for districts with a real supply-side relief signal already in
  `district_features_latest` (reservoir_pct_full > 40% or groundwater_trend='rising'), capped at
  30% of the pool per district, largest-remainder rounding so allocations sum exactly to the
  requested total.
- Verified against BigQuery: Marathwada-scoped 50-tanker request and all-district 100-tanker
  request both produce correct sums and real discount/cap trade-off narratives (e.g. Vijayapura,
  Sagar, Kutch discounted for reservoirs already >40% full).
- Agent instructions require surfacing every discount/cap/exclusion as an explicit trade-off,
  not a silent adjustment (PLAN.md §5 explainability requirement).

**Rainfall forecast (`weather_forecast` table, 2026-07-03)**
- `data-collection/ingestion/weather_forecast.py` — OpenWeatherMap's free 5-day/3-hour
  `/forecast` endpoint (same key as `weather_current.py`), aggregated into daily buckets
  (`expected_rain_mm`, `max_precip_probability`). This is the only genuinely forward-looking
  rainfall signal in the pipeline — CHIRPS/GEE precipitation is a ~1-month-lagged satellite
  estimate of the past, not a forecast. `WRITE_TRUNCATE` (rolling snapshot). 138 rows loaded
  across 23 districts.

**Farmer Advisory Agent (`agents/farmer_advisory_agent/`)**
- Built on ADK + Gemini 2.5 Flash. Tools: `get_risk_score` (reused from Triage Agent — same
  underlying model), `get_rainfall_forecast` ✅, `get_crop_advisory` ✅ — all verified
  end-to-end against BigQuery 2026-07-03.
- **RAG-corpus decision (2026-07-03)**: PLAN.md originally called for Vertex AI Search RAG
  over crop advisory/scheme docs. Deferred — no real document corpus collected yet. Instead,
  `data-collection/ingestion/generate_crop_advisory.py` generates citation-backed advisory
  rules via **Gemini + Google Search grounding** (not hand-research, not Claude WebSearch) —
  one call per district, asking for real ICAR/state agri-dept contingency-plan guidance
  (e.g. Latur: "complete soybean sowing by July 25, avoid fresh sowing beyond that" /
  "if cotton sowing delayed past July 23-29, switch to indigenous varieties and prefer tur").
  Every claimed `source_url` is cross-checked against the actual grounded search results
  (`grounding_metadata.grounding_chunks`); mismatches are replaced with a real grounded URL
  and flagged `verified_grounded=False` rather than trusted blindly. Upgrade path to full
  Vertex AI Search RAG once real advisory PDFs are collected.
- **Free-tier quota hit mid-run**: the Gemini Developer API key caps at 20 requests/day/model,
  not enough for 23 districts in one run. Switched to calling Gemini via the **Vertex AI
  backend** (`genai.Client(vertexai=True, project=...)`), billed against the already-linked
  GCP project instead of the free AI Studio quota — script supports `--retry-missing` to
  backfill only districts not yet in the seed CSV, used to fill in the remaining districts
  across two follow-up runs.
- All 23 districts now have ≥1 advisory rule (62 rows total in `crop_advisory`); verification
  rate varies per-district/per-call (inherent non-determinism in whether a given Gemini call's
  grounding chunks line up with its cited text) — this is treated as real signal, not a bug,
  and surfaced to the agent/user via `verified_grounded` rather than smoothed over.
- Agent instructions enforce responsible-AI framing: always cite source_url, flag
  unverified-grounded rules, never give a sowing/crop-switch recommendation from risk_score
  or forecast alone without checking `get_crop_advisory`, fall back to "consult local Krishi
  Vigyan Kendra" when confidence is low.

**Backend API (`backend/`, 2026-07-03)**
- FastAPI app, local dev via `uvicorn backend.main:app --reload --port 8080`.
- `backend/routers/districts.py` — read-only, non-agentic BigQuery reads for the admin console
  map/drill-down: `GET /api/districts` (all 23 districts, latest risk score, lat/lon for the
  map) and `GET /api/districts/{district_id}` (full drill-down: risk + explanation
  attributions + every underlying signal with its `as_of` string, mirroring the provenance
  requirement in PLAN.md section 5). Verified live against BigQuery — both endpoints tested
  end-to-end (Hingoli drill-down returns correct risk_score, attributions, and per-signal
  as-of stamps).
- `backend/routers/chat.py` + `backend/agent_runner.py` — one POST route per agent
  (`/api/chat/triage`, `/api/chat/allocation`, `/api/chat/farmer_advisory`), each wrapping an
  ADK `InMemoryRunner` (one runner per agent, reused across requests; sessions keyed by
  `(agent_name, session_id)`, in-memory only — lost on restart, fine for the hackathon demo).
  Returns `{reply, session_id, tool_calls}` — `tool_calls` surfaces which BigQuery-backed tool
  fired, for a debug/explainability view in the frontend later.
- Verified end-to-end: POST to `/api/chat/triage` correctly reached the Gemini call and
  triggered a real ADK tool-call flow; got a `429 RESOURCE_EXHAUSTED` from the free-tier
  20-req/day Gemini quota (same limit already documented above for
  `generate_crop_advisory.py`), confirming the routing/session/runner wiring is correct — the
  quota, not the backend, is the blocker. Re-verify a full reply once quota resets or by
  switching the agents to the Vertex AI backend (`genai.Client(vertexai=True, ...)`, billed
  against `climate-resilience-in`) the way `generate_crop_advisory.py` already does.
- CORS wide open (`allow_origins=["*"]`) since the frontend's dev port isn't fixed yet —
  tighten before any real deployment.
**Cloud Run deployment (2026-07-03)**
- `Dockerfile` (repo root, `python:3.13-slim`, installs `backend/requirements.txt` +
  `agents/requirements.txt`, copies only `backend/` + `agents/` — `data-collection/` and docs
  excluded via `.dockerignore`) and deployed with
  `gcloud run deploy climate-resilience-api --source . --region asia-south1`.
- Live at `https://climate-resilience-api-731583000008.asia-south1.run.app` — public/
  unauthenticated (PLAN.md's admin/farmer IAM separation is still deferred), 512Mi/120s timeout.
- `GOOGLE_API_KEY` supplied via Secret Manager (`google-api-key` secret, `secretAccessor` role
  granted to the default compute service account `731583000008-compute@developer.gserviceaccount.com`)
  rather than a plain env var, so it doesn't show up in `gcloud run services describe` output.
  `GCP_PROJECT`/`BQ_DATASET` set as plain env vars (not sensitive).
- Verified live end-to-end post-deploy: `/health`, `/api/districts`, `/api/districts/{id}`, and
  `/api/chat/triage` (a real "top 3 riskiest districts" query correctly called
  `list_top_risk_districts` + `get_risk_score` x3 and returned a grounded, cited answer —
  confirms BigQuery access, the Gemini secret, and the ADK runner all work against the deployed
  container, not just local dev).
- Not yet done: auth/IAM separation between admin and farmer-facing endpoints (PLAN.md section
  2's "Identity/IAM" line item), CI/CD for redeploys (current deploy was a manual
  `gcloud run deploy --source .` run).

**Frontend (`frontend/`, 2026-07-03)**
- React + Vite (JS, not TS), `react-router-dom` for routing, `leaflet`/`react-leaflet` for the map.
  No Looker Studio embed — went with a custom Leaflet map instead for tighter control over
  marker click → drill-down wiring.
- `src/api.js` — thin fetch wrapper over the Cloud Run backend, base URL from `VITE_API_BASE`
  (`.env.development` points at the live Cloud Run URL directly, since there's no local BigQuery
  proxy — the frontend always talks to the deployed backend, even in dev).
- Two routes: `/admin` (`pages/AdminConsole.jsx`) and `/farmer` (`pages/FarmerChat.jsx`), shared
  nav shell in `components/Layout.jsx`.
- Admin console: `components/DistrictMap.jsx` (Leaflet circle markers colored by `risk_score`,
  click → select), `components/DistrictDrilldown.jsx` (risk score, top feature attributions,
  every underlying signal with its `as_of` string — mirrors the provenance requirement in
  PLAN.md section 5), and a Triage/Allocation tab switcher over a shared `components/ChatPanel.jsx`
  (session_id persisted per agent, `tool_calls` shown in a collapsible debug view).
- Farmer page reuses the same `ChatPanel` wired to `/api/chat/farmer_advisory`, plain mobile-first
  layout, no map.
- Verified end-to-end with Playwright against the live Cloud Run backend (no local API proxy):
  map renders real district markers from `GET /api/districts`, clicking a marker (Hingoli) loads
  the drill-down with real risk score (89.9), attributions, and signal as-of stamps from
  `GET /api/districts/{id}`, tab switching between Triage/Allocation chat panels works, farmer
  chat page renders cleanly. Zero console errors. Did not complete a full chat round-trip in this
  verification pass (would hit the paid Gemini API) — chat wiring itself was already verified
  from the backend side in the API section above.
- Not yet done: Looker Studio embed (skipped in favor of the custom map), mobile responsiveness
  beyond a basic breakpoint, WhatsApp/SMS interface (stretch goal per PLAN.md).

### Not started
- Full Vertex AI Search RAG corpus (crop advisory PDFs, MGNREGA guidelines, drought playbooks) — deferred in favor of the Gemini+Search-generated `crop_advisory` table above
- Cloud Translation / localization (all agents still English-only, plain text)
- Cloud Functions / Scheduler automation for recurring ingestion (all pulls currently run manually via `data-collection/run_all.py`)
- Deploying the frontend itself (currently only verified via local `npm run dev`; not yet pushed to Firebase Hosting/Cloud Run)

## Next up
1. Deploy the frontend (Firebase Hosting or a second Cloud Run service) so the demo has a public URL, not just local dev
2. Full Vertex AI Search RAG corpus, if time allows, as an upgrade over the curated `crop_advisory` table
3. Auth/IAM separation between admin and farmer-facing endpoints before any real deployment beyond the demo
