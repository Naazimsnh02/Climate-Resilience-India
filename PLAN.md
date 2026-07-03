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

**Triage Agent** (admin-facing)
- Input: "show me top 20 districts at risk" or map click
- Tools: `query_bigquery(sql)`, `get_risk_score(district_id)`, `get_historical_analog(district_id)`
- Output: ranked list with the *why* — rainfall deficit %, reservoir days-remaining, historical analog year (e.g., "similar to 2015-16 drought in this district")

**Allocation Agent** (admin-facing)
- Input: "I have 50 water tankers, allocate across Marathwada"
- Tools: same BigQuery access + a constraint-satisfaction/optimization step (can be a simple greedy/linear allocation in Python called as a tool, not necessarily ML)
- Output: allocation table + rationale, flags trade-offs ("District X deprioritized despite high risk because reservoir refill is expected from upstream release")

**Farmer Advisory Agent** (citizen-facing)
- Input: free text/voice, village or district context
- Tools: RAG over crop advisory + government scheme docs (Vertex AI Search), `get_risk_score`, `get_rainfall_forecast`
- Output: plain-language, localized answer with confidence and source citation; falls back to "consult local agri officer" when confidence is low — important for responsible AI framing

All three share the same underlying `district_risk_score` table so the story is consistent: one model, multiple decision surfaces.

---

## 5. Explainability / Responsible AI (explicit judging criterion)

- Every recommendation shows: which data points drove it (rainfall deficit %, reservoir %, historical analog), not just a black-box score
- Confidence bands on forecasts (Vertex Forecasting gives prediction intervals — surface them)
- Farmer agent explicitly declines to give overconfident advice when data is sparse (e.g., groundwater is quarterly — say so)
- Data provenance and as-of timestamps shown in UI (especially for Tier 2 sources) so users know freshness

---

## 6. Build sequence (no cut-down — full scope, sequenced)

1. **Data ingestion**: stand up Cloud Functions for IMD, Agmarknet, OpenWeatherMap; GEE export script for NDVI/CHIRPS/soil moisture; one-time load of Tier 2 (CWC/CGWB/NRSC snapshot) into BigQuery
2. **Warehouse**: finalize BigQuery schema above, load `district_master` (boundaries + crop calendar — from Census/Agri Census open data)
3. **Risk model**: BigQuery ML logistic/regression baseline for `district_risk_score`, iterate to Vertex AI custom forecasting for reservoir depletion trajectory if time allows
4. **RAG corpus**: collect crop advisory PDFs (ICAR, state agri dept), MGNREGA drought-works guidelines, past drought response playbooks → Vertex AI Search index
5. **Agents**: build Triage, Allocation, Farmer Advisory agents on ADK, wire tool-calling to BigQuery + RAG index
6. **Backend API**: Cloud Run service exposing agent endpoints + risk data endpoints
7. **Frontend**: admin console (map + drill-down, Looker Studio embed or custom React map with district choropleth) + farmer chat UI
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
- Confirm IMD API is actually reachable and returns data for target districts (has known uptime issues) — test first, have Tier-2-style seeded fallback ready even for rainfall if it's down
- Confirm GEE account access is provisioned under whatever GCP project/credits the hackathon provides
- Decide real districts to seed as demo hero examples (recommend picking 3-5 from the "150-200 flagged" belt: e.g., a Marathwada district, a Rajasthan district, an eastern UP district) for a concrete, verifiable demo rather than all-India abstraction
