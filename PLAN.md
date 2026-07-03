# El Niño 2026 Decision Copilot — Full Build Plan

Gen AI Academy APAC Hackathon. Goal: AI-powered decision intelligence platform for India's El Niño 2026 monsoon/drought crisis, targeting district administrators and farmers, built on Google Cloud.

Grounding facts (see conversation / news, July 2026): IMD forecasts ~90-92% of normal monsoon rainfall, NOAA confirms El Niño intensifying toward "super El Niño," 150-200 districts flagged as priority watch (Marathwada–north Karnataka belt, Rajasthan, Gujarat, MP, Chhattisgarh, eastern UP, Bihar, Jharkhand), reservoir storage fell 38.7%→34.5% of capacity in two weeks, 90% of kharif rice/maize/soy/pulses area is rainfed, heatwaves hitting 45-50°C.

Real data sources confirmed in `DATA_SOURCES.md` — build against Tier 1 (IMD rainfall API, Agmarknet prices, OpenWeatherMap, Google Earth Engine NDVI/CHIRPS/soil moisture) and seed Tier 2 (CWC reservoirs, CGWB groundwater, NRSC drought bulletins) as a periodically-refreshed static table.

---

## 1. Product shape

Two front doors, one backend brain:

1. **Administrator Console** (district collectors / agriculture dept / disaster management officers)
   - District risk map of India, ranked by drought severity trajectory
   - Drill into a district: rainfall deficit, reservoir days-remaining, groundwater trend, crop-stress signal, recommended interventions, and *why* (explainability panel)
   - Resource allocation assistant: "I have N water tankers / X crore relief budget — where do they go first?"
   - Natural-language query over all ingested data ("which districts have both reservoir <30% and no positive-IOD rainfall relief expected in next 15 days?")

2. **Citizen/Farmer Advisory** (mobile-first, voice + text, regional language)
   - "Should I sow paddy this week?" / "When should I switch to millet?"
   - Localized to village/taluka using the same underlying risk model
   - Explains its reasoning in plain language, cites the data behind it
   - Works via WhatsApp/SMS-style interface for low-bandwidth access (stretch goal), web chat for the demo

Both consume the same **Decision Intelligence Core**: ingestion → risk model → reasoning agent → explanation layer.

---

## 2. Architecture

```
                     ┌─────────────────────────────────────────┐
                     │           DATA INGESTION LAYER            │
                     │  Cloud Functions / Cloud Run jobs (cron)   │
                     ├─────────────────────────────────────────┤
 IMD Rainfall API ──▶│                                           │
 Agmarknet API    ──▶│   Scheduled pullers → Cloud Storage (raw) │
 OpenWeatherMap    ─▶│   → transform → BigQuery (structured)     │
 Google Earth Eng ──▶│                                           │
 (NDVI/CHIRPS/soil)  │                                           │
 CWC/CGWB/NRSC       │   Tier-2: manual/scraped snapshot loader  │
 (seeded, refreshed  │   → BigQuery, timestamped as-of date       │
  weekly/quarterly)  │                                           │
                     └─────────────────────────────────────────┘
                                     │
                                     ▼
                     ┌─────────────────────────────────────────┐
                     │            BigQuery (warehouse)            │
                     │  district_rainfall, reservoir_levels,      │
                     │  groundwater, mandi_prices, ndvi_soilmoist,│
                     │  district_master (boundaries, population,  │
                     │  crop calendar, historical drought years)  │
                     └─────────────────────────────────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                                 ▼
       ┌─────────────────────────┐       ┌─────────────────────────────┐
       │   PREDICTION LAYER        │       │   RAG / KNOWLEDGE LAYER       │
       │   Vertex AI (BigQuery ML  │       │   Vertex AI Search / matching │
       │   or a Vertex custom      │       │   engine over: crop advisory  │
       │   forecasting model)      │       │   docs, historical drought    │
       │   → district_risk_score,  │       │   response playbooks, MGNREGA │
       │   days-to-critical-       │       │   scheme docs, local language │
       │   reservoir, crop-stress  │       │   agri-extension material     │
       │   trajectory              │       │                               │
       └─────────────┬────────────┘       └───────────────┬───────────────┘
                     │                                     │
                     └───────────────┬─────────────────────┘
                                     ▼
                     ┌─────────────────────────────────────────┐
                     │        REASONING / AGENT LAYER             │
                     │  Gemini 2.x on Vertex AI + Agent           │
                     │  Development Kit (ADK)                     │
                     │  - District triage agent (ranks + explains)│
                     │  - Resource allocation agent (constraint-  │
                     │    aware: budget/tankers vs. need)         │
                     │  - Farmer advisory agent (RAG + forecast,  │
                     │    conversational, multilingual)           │
                     │  Tool-calling into BigQuery for live facts │
                     └─────────────┬───────────────────────────┘
                                     ▼
                     ┌─────────────────────────────────────────┐
                     │             APPLICATION LAYER              │
                     │  Cloud Run (backend API, FastAPI/Node)     │
                     │  Frontend: React/Next.js on Cloud Run or   │
                     │  Firebase Hosting                          │
                     │  - Admin console (map + drill-down + chat) │
                     │  - Citizen chat (web now, WhatsApp stretch)│
                     │  Looker Studio embedded dashboard for       │
                     │  district officers (fast to build, good    │
                     │  demo polish)                               │
                     └─────────────────────────────────────────┘
```

### Google Cloud services used
- **BigQuery** — central warehouse, also BigQuery ML for a fast baseline risk-scoring model if Vertex custom training is too slow to stand up
- **Vertex AI** — Gemini for the agent/reasoning layer, Vertex AI Search (RAG) for advisory docs, optionally Vertex Forecasting for reservoir depletion / rainfall trajectory
- **Agent Development Kit (ADK)** — structure the three agents (triage, allocation, farmer advisory) with tool-calling into BigQuery and clear system instructions per persona
- **Cloud Run** — backend API + frontend hosting, serverless and fast to deploy for a hackathon timeline
- **Cloud Functions / Cloud Scheduler** — scheduled data pullers (IMD, Agmarknet, OpenWeatherMap, GEE exports) running every few hours/daily
- **Cloud Storage** — raw data landing zone before BigQuery load
- **Google Earth Engine** — NDVI, CHIRPS precipitation, soil moisture layers, GCP-linked
- **Looker Studio** — fast dashboard layer for the admin console / demo polish, backed directly by BigQuery
- **Cloud Translation API** — regional language support for the farmer advisory agent (Hindi, Marathi, Kannada, etc. matching the flagged-district belt)
- **Identity/IAM** — basic role separation between admin console and public farmer-facing endpoint

---

## 3. Data model (BigQuery, core tables)

- `district_master(district_id, state, name, population, geometry, kharif_crop_mix, historical_drought_years)`
- `rainfall_daily(district_id, date, actual_mm, normal_mm, deficit_pct, source)`
- `reservoir_status(reservoir_id, district_id, date, live_storage_pct, pct_of_10yr_normal, pct_of_last_year, source='CWC bulletin', as_of_date)`
- `groundwater_level(district_id, station_id, quarter, level_m, trend, source='CGWB', as_of_date)`
- `mandi_prices(commodity, mandi_id, district_id, date, modal_price, min_price, max_price)`
- `ndvi_soil_moisture(district_id, date, ndvi, soil_moisture_pct, source='GEE')`
- `district_risk_score(district_id, date, risk_score, days_to_critical_reservoir, rainfall_deficit_rank, model_version, explanation_json)` — output of prediction layer, consumed by agents

---

## 4. Agent design (ADK + Gemini)

**Triage Agent** (admin-facing) — ✅ built (`agents/triage_agent/`, ADK + Gemini 2.5 Flash), verified end-to-end 2026-07-03
- Input: "show me top 20 districts at risk" or map click
- Tools: `get_risk_score(district_id)` ✅, `list_top_risk_districts(limit)` ✅, `get_historical_analog(district_id)` ✅ wired to a new WebSearch-researched, citation-backed `historical_drought_years` table; `query_bigquery(sql)` — not yet built
- Output: ranked list with the *why* — rainfall deficit %, reservoir days-remaining, historical analog year (e.g., "similar to 2015-16 drought in this district")

**Allocation Agent** (admin-facing) — ✅ built (`agents/allocation_agent/`, ADK + Gemini 2.5 Flash), verified end-to-end 2026-07-03
- Input: "I have 50 water tankers, allocate across Marathwada"
- Tool: `allocate_resources(total_units, resource_name, scope_state, scope_belt, district_ids)` — deterministic, non-LLM allocation (risk-proportional, discounted for districts with a real supply-side relief signal already in `district_features_latest`, capped at 30%/district, largest-remainder rounding), not an LLM decision, so it's auditable
- Output: allocation table + rationale, flags trade-offs (e.g. "Vijayapura deprioritized despite high risk because its reservoir is already at 77% full" — grounded in real fields, not a fabricated "upstream release" signal)

**Farmer Advisory Agent** (citizen-facing) — ✅ built (`agents/farmer_advisory_agent/`, ADK + Gemini 2.5 Flash), verified end-to-end 2026-07-03
- Input: free text/voice, village or district context
- Tools: `get_risk_score` ✅ (reused from Triage Agent), `get_rainfall_forecast` ✅ wired to a new `weather_forecast` table (OpenWeatherMap 5-day forecast — the only genuinely forward-looking rainfall signal in the system), `search_advisory_corpus` ✅ (real Vertex AI Search RAG, primary source), `get_crop_advisory` ✅ wired to a new `crop_advisory` table (fallback)
- **Full Vertex AI Search RAG — built 2026-07-03**: real ICAR-CRIDA District Agriculture Contingency Plan PDFs, one per seed district (23/23 found district-exact, manifest in `data-collection/seed/rag_corpus_manifest.csv`), staged in `gs://climate-resilience-in-raw/rag-corpus/{district_id}/` and indexed in a Vertex AI Search (Discovery Engine) data store (`crop-advisory-corpus`) + search app (`crop-advisory-search`). `search_advisory_corpus` queries it and returns real cited passages. `get_crop_advisory` (Gemini + Google Search grounding-generated rules, source URLs cross-checked against actual grounding chunks) is now the fallback for districts/questions the real corpus doesn't cover, not the primary source.
- Output: plain-language answer with confidence and source citation (a real contingency-plan document title/URI, or the fallback's source_url); falls back to "consult local Krishi Vigyan Kendra/agri officer" when confidence is low or an advisory rule is unverified — important for responsible AI framing. Localization (Cloud Translation) not yet built — English only.

All three share the same underlying `district_risk_score` table so the story is consistent: one model, multiple decision surfaces.

---

## 5. Explainability / Responsible AI (explicit judging criterion)

- Every recommendation shows: which data points drove it (rainfall deficit %, reservoir %, historical analog), not just a black-box score
- Confidence bands on forecasts (Vertex Forecasting gives prediction intervals — surface them)
- Farmer agent explicitly declines to give overconfident advice when data is sparse (e.g., groundwater is quarterly — say so)
- Data provenance and as-of timestamps shown in UI (especially for Tier 2 sources) so users know freshness

---

## 6. Build sequence (no cut-down — full scope, sequenced)

1. **Data ingestion** ✅ — Tier 1 (GEE CHIRPS/NDVI/SMAP, Agmarknet/data.gov.in mandi prices, OpenWeatherMap, data.gov.in rainfall) live in BigQuery for 23 seed districts; Tier 2 (CWC/CGWB/NRSC) seeded as a static snapshot table. IMD direct API dropped (no self-serve key). Cloud Functions/Scheduler automation for recurring pulls not yet done (scripts currently run manually via `data-collection/run_all.py`).
2. **Warehouse** ✅ — BigQuery schema above live in `raw_data` (`climate-resilience-in` project), `district_master` loaded for 23 seed districts.
3. **Risk model** ✅ (baseline) — BigQuery ML linear regression baseline live (`data-collection/modeling/build_risk_model.py`), `district_risk_score` populated with `ML.EXPLAIN_PREDICT` attributions. This is a calibrated composite index dressed as ML, not a validated predictive model — see the long-term roadmap below for what "real" looks like.
4. **RAG corpus** ✅ — 23/23 seed districts' real ICAR-CRIDA District Agriculture Contingency Plan PDFs collected, staged in GCS, indexed in a Vertex AI Search data store/app, wired into the Farmer Advisory Agent as `search_advisory_corpus`. MGNREGA drought-works guidelines and past drought response playbooks not yet added (see PROGRESS.md "Not started").
5. **Agents**: all three built, ADK + Gemini 2.5 Flash — Triage Agent ✅ (get_risk_score, list_top_risk_districts, get_historical_analog), Allocation Agent ✅ (allocate_resources), Farmer Advisory Agent ✅ (get_risk_score, get_rainfall_forecast, get_crop_advisory).
6. **Backend API**: ✅ built and deployed — `backend/` (FastAPI) on Cloud Run at `https://climate-resilience-api-731583000008.asia-south1.run.app`, verified end-to-end 2026-07-03 — `GET /api/districts`, `GET /api/districts/{id}` (BigQuery reads), `POST /api/chat/{triage,allocation,farmer_advisory}` (ADK `InMemoryRunner` per agent). Public/unauthenticated for the demo; IAM separation between admin/farmer endpoints still open.
7. **Frontend**: ✅ built (`frontend/`, React + Vite + react-router-dom + Leaflet) — admin console (district risk map + drill-down + Triage/Allocation chat tabs) and farmer chat UI, verified end-to-end against the live Cloud Run API with Playwright 2026-07-03. Went with a custom Leaflet map rather than a Looker Studio embed. Not yet deployed to a public URL (local dev only so far).
8. **Localization**: Cloud Translation for at least 2-3 languages matching flagged districts (Hindi, Marathi, Kannada)
9. **Demo narrative**: seed with real current data (today's rainfall deficit, current reservoir %), walk through one flagged district end-to-end — risk detected → admin allocates resources → farmer gets sowing advice — closing the full decision loop

---

## 7. Team split (if multi-person)

- **Data/ML**: ingestion pipelines, BigQuery schema, risk model
- **Agents/Backend**: ADK agents, Cloud Run API, RAG corpus curation
- **Frontend**: admin console + farmer chat UI, Looker Studio dashboard
- **Narrative/Demo**: real-data storytelling, slide deck, judging-criteria alignment (explainability, responsible AI, multi-track coverage)

---

## Open questions to resolve before coding starts
- ~~Confirm IMD API is actually reachable~~ — resolved: no self-serve key exists, dropped as a live source (see `DATA_SOURCES.md`)
- ~~Confirm GEE account access is provisioned~~ — resolved: registered, live and pulling CHIRPS/NDVI/SMAP
- ~~Decide real districts to seed as demo hero examples~~ — resolved: 23 districts across the flagged belt in `district_master.csv`

---

## 8. Long-term roadmap: model quality + full-India coverage

Where the risk model stands today (2026-07-03): a BQML linear regression over 23 hand-seeded districts, trained to reproduce a hand-parsed drought-bulletin ordinal (`drought_status.status` text → 1-4 score). At n=23 with no held-out split, this is a calibrated composite index dressed as ML, not a validated predictive model. Path to something real:

1. **Add a time axis.** Every source except `rainfall_daily` is a single snapshot per district today (`ndvi_soil_moisture`, `reservoir_status`, `groundwater_level`). Turning these into true daily/weekly time series is the single highest-leverage change — it lets the model learn *trajectories* (reservoir decline rate, rainfall deficit trend) instead of a point-in-time composite, and unlocks Vertex AI Forecasting for `days_to_critical_reservoir` with real prediction intervals, replacing today's flat 0.3pp/day heuristic.
2. **Get a real label.** `drought_status.status` is scraped free text, not rigorous ground truth. Long-term: backtest against actual historical drought-year outcomes (crop yield loss, MGNREGA work-demand spikes, or IMD's own drought classification) for districts with multi-year history, so the model is validated against something with real stakes rather than circularly trained against a label built from similar inputs.
3. **Scale from 23 to ~750 districts.** `district_master` + GEE pulls parameterize cleanly over lat/lon (data-entry expansion, not architecture change). Tier 2 (CWC/CGWB/NRSC) is the hard part — not scrapable per `DATA_SOURCES.md` findings, so 750 districts of hand-researched CSVs won't scale. Worth a real IMD API application and revisiting India-WRIS's WIMS handshake for reservoir telemetry at that point. Mandi prices already cover far more districts than are seeded — cheap to widen first.
4. **Unblock IMD.** The one clean current-conditions, full-district-granularity rainfall source has no self-serve key. CHIRPS (current proxy) lags ~1 month and is satellite-inferred, not ground-truth station data. Worth applying directly to IMD in parallel with other build work.
5. **Guard against silent data rot.** Already burned once (SMAP10KM deprecated 4 years ago, would have silently poisoned the model if not caught manually). At scale, add a scheduled freshness check per source (compare `*_asof` against expected cadence, alert on staleness) instead of relying on catching it during a build session.
6. **Retraining cadence + drift monitoring.** Once real time series exist, retrain on a schedule (e.g. weekly, ahead of each CWC Thursday bulletin) and track prediction drift/calibration over a season — feeds the confidence-bands requirement in section 5 rather than a single static fit.
