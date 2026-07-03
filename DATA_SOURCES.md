# Real Data Sources — El Niño 2026 Decision Intelligence Platform

Researched 2026-07-03. Status column reflects what's confirmed usable for a hackathon build vs. what needs a registration/lag/manual-download workaround.

## Live-tested access status (2026-07-03, against GCP project `climate-resilience-in`)

Actually hit these endpoints instead of trusting docs. Results:

| Source | Test | Result | Action needed |
|---|---|---|---|
| IMD API (`api.imd.gov.in/api/v1/districtrainfall`) | `curl` the endpoint directly | **401 `{"error":"API key missing"}`** — and there is no self-serve signup flow documented anywhere on the IMD API reference page. This is a real blocker, not a formality. | Deprioritized as primary source. Would need to email/apply to IMD directly — too slow for hackathon timeline. |
| Google Earth Engine (`earthengine-api` Python) | `ee.Initialize(project='climate-resilience-in')` | **Blocked**: `Project climate-resilience-in is not registered to use Earth Engine`. One-time manual step (accept noncommercial-use terms in browser). | **User action required**: visit `https://console.cloud.google.com/earth-engine/configuration?project=climate-resilience-in`, register for noncommercial use. Takes ~1 minute, cannot be done via CLI (ToS click-through). |
| data.gov.in (mandi prices resource page) | `curl` resource page | HTTP 200, but API access requires a registered account + API key (self-serve signup, not instant-anonymous). | **User action required**: register at data.gov.in, generate API key from "My Account". |
| Agmarknet API | Not yet tested | Same registration model as data.gov.in likely | **User action required**: register for API key. |
| OpenWeatherMap | Not yet tested | Free tier, self-serve, historically instant | **User action required**: sign up, generate key (fastest of the four). |

**Net effect on the plan**: none of the Tier-1 "live API" sources are actually zero-friction. Every one of them needs either a one-time manual registration/ToS click (Earth Engine, data.gov.in, Agmarknet, OpenWeatherMap) or is a dead end for hackathon timelines (IMD direct API). This doesn't change the architecture, but it does mean data collection can't be fully automated end-to-end without ~15 minutes of manual account setup first. Recorded here so we don't re-discover this mid-build.

## Ingestion scaffolding built + live-run findings (2026-07-03)

GCP project `climate-resilience-in` created, billing linked, BigQuery dataset `raw_data` + GCS bucket live. `data-collection/` scaffolding built and actually run end-to-end (not just written) against 23 seed districts. Findings from that live run, so the next person doesn't have to rediscover them:

- **Agmarknet has no separate developer portal.** What guides call "the Agmarknet API" is the same data.gov.in OGD resource (`9ef84268-d588-465a-a308-a864a43d0070`, "Current Daily Price of Various Commodities from Various Markets (Mandi)"). One `DATA_GOV_IN` key covers both. Confirmed live and updating same-day (`updated_date` matched 2026-07-03).
- **api.data.gov.in silently stalls on Python `requests`' default User-Agent** — every call hung to a read-timeout with zero error response, while the identical URL via `curl` returned in under a second. Fixed by sending `User-Agent: curl/8.4.0`. This looks like an undocumented WAF rule blocking non-browser-like UAs; not a rate limit or key issue. Applies to both `mandi_prices.py` and `rainfall_datagovin.py`.
- **CHIRPS daily precipitation (Earth Engine) lags real time** — querying "last 30 days from today" returned an empty collection and threw (not just returned nulls). Fixed by anchoring the window on the latest image actually present in the collection (`sort` + `first()`) rather than wall-clock "now". Latest available CHIRPS data as of this run: **2026-05-31** (~1 month lag).
- **`NASA_USDA/HSL/SMAP10KM_soil_moisture` (the soil moisture dataset originally planned) is dead** — its own GEE catalog page flags it deprecated, and the live run confirmed its latest image is from **2022-08-02**, i.e. it stopped updating almost 4 years ago. This would have silently poisoned the drought model with stale soil-moisture data if not checked. **Swapped to `NASA/SMAP/SPL4SMGP/008`**, verified current through **2026-06-30**.
- **MODIS NDVI (`MODIS/061/MOD13Q1`)** is current: latest composite as of this run is **2026-05-25** (16-day compositing cadence, so ~5-week lag is expected/normal, not a problem).
- **OpenWeatherMap**: newly generated key returned 401 on first use. This matches OpenWeatherMap's known behavior of a delay (historically up to ~2 hours) before a fresh key activates — not a code bug. Retry later; script is otherwise ready.
- Every ingestion script now records an **as-of / pulled-at timestamp per source** (`precip_asof`, `ndvi_asof`, `soil_moisture_asof`, `pulled_at`) specifically so the app layer can show data freshness/staleness per signal rather than presenting everything as equally "live."

## Rainfall (data.gov.in) — resolved and wired in (2026-07-03)

User found two candidate resources on the (JS-rendered, unscrapeable) data.gov.in rainfall catalog and asked which one we needed:
- **"Daily District-wise Rainfall Data"** — `6c05cd1b-ed59-40c2-bc31-e314f39c6971` ← **this is the correct one**, matches our district-level granularity (fields: State, District, Date, Year, Month, Avg_rainfall, Agency_name; agency is "NRSC VIC MODEL")
- "Daily Sub-basin-wise Rainfall Data" — `da428447-700a-41e9-a56a-d7855ffb672f` — wrong granularity for us (Basin/Subbasin, not District), not used

Both are from Department of Water Resources, River Development & Ganga Rejuvenation / Ministry of Jal Shakti / NWIC, and both show portal metadata `"updated_date": "2025-12-31"`.

Wired into `rainfall_datagovin.py` and live-tested. More findings from that testing:

- **This dataset predates the 2023 Maharashtra/Gujarat district renames.** Filtering by the current official names returns zero records. Must use: `Aurangabad` (not Chhatrapati Sambhajinagar), `Osmanabad` (not Dharashiv), `Kachchh` (not Kutch), `Banas Kantha` — two words — (not Banaskantha). Karnataka's renames (Kalaburagi/Gulbarga, Vijayapura/Bijapur) are *not* an issue here — this dataset already uses the current names for those. Fixed by adding a `datagovin_district_name` column to `district_master.csv` that carries whatever name this specific API expects per district, decoupled from our canonical `name` column.
- **The API hard-caps every response at 10 records regardless of the requested `limit`** (confirmed: `limit=1000` still returned `count=10`, response echoed back `"limit": "10"`). This is not documented anywhere. Pagination via `offset` is mandatory. This same bug was silently truncating `mandi_prices.py` to 10 records per state before we caught it and fixed both scripts.
- **The state/district `filters[...]` params are not a strict/exact match** — a mandi-prices pull scoped to 9 specific states came back with extra rows for Andhra Pradesh, Arunachal Pradesh, and Himachal Pradesh that were never requested. The underlying platform is Elasticsearch-backed and the filters appear to be analyzed/fuzzy rather than exact-term. **Anyone consuming this API should client-side re-filter on the returned `State`/`District` fields rather than trust the request filter alone** — not yet added to our scripts, flagged as a follow-up.
- **Without an explicit sort, pagination returns arbitrary old records, not recent ones.** A live pull for all 23 districts came back with `MAX(Date)` per district landing in **2019-2020** — nowhere close to the portal's claimed Dec-2025 update. The portal's "updated on" date describes when the index was last touched, not the recency of what an unsorted query returns. Attempted to fix with `sort[Date]=desc` but got rate-limited (`429`) before confirming it works — **follow-up needed**: test `sort[Date]=desc` (or equivalent) once the rate limit window clears, otherwise this source is only useful as a multi-year historical baseline, not a current-conditions signal.
- **Net effect**: this dataset is confirmed real and now flowing into BigQuery (`rainfall_daily`, 2,070 rows across 23 districts), but per the caveats above it is a **historical/backfill cross-check, not a current-conditions source**. GEE's CHIRPS precipitation (`gee_pull.py`, `precip_mm_30d`, current through 2026-05-31) remains the live rainfall signal for the risk model.

## Rate limiting (data.gov.in) — discovered under real load

Sustained use during this session (many curl tests + two full 23-district/9-state ingestion runs back to back) triggered `429 Too Many Requests` — first seen as a total stall (no error, just a hang) when testing manually, then as explicit 429s once pagination started firing many sequential requests. Not documented anywhere with a rate (requests/min or /hour). Handled with:
- Exponential backoff retry (1s, 2s, 4s, 8s, 16s) per request in both `mandi_prices.py` and `rainfall_datagovin.py`
- Non-fatal skip-and-continue at the state/district level once retries are exhausted, so one throttled state doesn't abort the whole run
- A small fixed delay between successive paginated calls to reduce how often the limit is hit in the first place

Real-world effect: in the mandi-prices run, **Maharashtra and Rajasthan were skipped** after exhausting retries (everything else succeeded, ending with 4,958 total rows across 8 states). These two can be backfilled by rerunning `mandi_prices.py` alone later, ideally with some idle time first — the `WRITE_APPEND` disposition means a rerun adds to, not replaces, what's already loaded (dedupe if rerunning the same state twice).

## Lesson learned: batch-at-the-end loading is risky for slow scripts

Both `mandi_prices.py` and `rainfall_datagovin.py` accumulate all records in a Python list across every state/district and only call `load_dataframe()` once at the very end. During this session, a mandi-prices run took **~14 minutes** (large states like Madhya Pradesh alone had ~1,900 records across ~190 paginated calls), and partway through it looked stalled — but killing it would have discarded everything already fetched, since nothing had been written to BigQuery yet. Got this wrong once already (killed a Google Earth Engine pull prematurely for the same reason, losing ~8 minutes of work and having to rerun it). **Follow-up improvement**: load incrementally per-state/per-district (or checkpoint periodically) instead of one big batch at the end, so a slow or interrupted run doesn't lose already-fetched progress and doesn't tempt a premature kill.

## Citation: how the 150-200 flagged districts / seed list was chosen

The claim that ~150-200 districts are on priority watch for the 2026 El Niño monsoon (Marathwada–north Karnataka belt, Rajasthan, Gujarat, MP, Chhattisgarh, eastern UP, Bihar, Jharkhand) — used to pick the 23 representative districts in `district_master.csv` — comes from: [Around 200 districts flagged for El Nino impact as weak monsoon forecast puts agriculture ministry in crisis mode](https://www.downtoearth.org.in/agriculture/around-200-districts-flagged-for-el-nino-impact-as-weak-monsoon-forecast-puts-agriculture-ministry-in-crisis-mode) (Down To Earth, 2026).

## 1. Rainfall (IMD)

| Source | What it gives | Access | Status |
|---|---|---|---|
| **IMD public API** — `https://api.imd.gov.in/api/v1/districtrainfall?id=<district_id>` | Daily actual vs. normal rainfall, weekly + cumulative, per district | Public REST endpoint, no key found required in docs (`api.imd.gov.in/public/api_reference.html`) | ✅ Best primary source — verify live during setup, IMD endpoints have a history of flakiness/downtime |
| **data.gov.in "Rainfall" catalog** | Station-wise (CWC/state WRD/APWRIMS) + IMD/NRSC gridded rainfall, daily normal rainfall by district | Needs `data.gov.in` account → API key from "My Account" | ✅ Fallback/backfill source, also good for historical baseline |
| **IMD gridded rainfall (0.25°×0.25°)** — `imdpune.gov.in/cmpg/Griddata` | 1901–2024 daily gridded rainfall, binary format | Free download, no API | ⚠️ Use for historical/normal-year comparison only (binary parsing, not real-time) |

## 2. Reservoir / Surface Water (CWC)

| Source | What it gives | Access | Status |
|---|---|---|---|
| **India-WRIS** (`indiawris.gov.in`) | Reservoir module: daily level + live storage for monitored reservoirs, telemetry-fed | Web portal; API access exists via WIMS handshake but public API docs are thin | ⚠️ Likely need to scrape/download CSV exports from the WRIS dashboard rather than clean REST calls — validate early |
| **CWC Reservoir Level & Storage Bulletin** | Weekly bulletin (every Thursday): live storage for 123 major reservoirs, vs. last year and vs. 10-yr normal, state-wise and all-India | PDF/web bulletin at `cwc.gov.in/en/reservoir-level-storage-bulletin` | ✅ Reliable for demo narrative ("reservoirs at X% of normal") but is PDF/weekly, not an API — plan to parse or hand-enter for demo |

## 3. Groundwater (CGWB)

| Source | What it gives | Access | Status |
|---|---|---|---|
| **CGWB / India-WRIS groundwater module** | ~25,000 National Hydrograph Network Stations, district-station level, but only **4 readings/year** (Jan, May, Aug, Nov) | Portal `gwdata.cgwb.gov.in`, also mirrored on data.gov.in | ⚠️ Too sparse for real-time decisioning — use as a slow-moving baseline signal, not a live feed. One data.gov.in groundwater resource explicitly says "API does not exist, submit request" |

## 4. Crop Prices / Market Stress (Agmarknet)

| Source | What it gives | Access | Status |
|---|---|---|---|
| **Agmarknet 2.0 API** | Daily wholesale/min/max/modal prices, 200+ commodities, 3,000+ mandis, ~2M records/month | Registered API key, RESTful | ✅ Good proxy signal — price spikes in a district = early economic stress indicator correlating with local crop failure |
| **data.gov.in mirror** ("Current daily price of various commodities...") | Same underlying data, OGD-hosted | API key via data.gov.in | ✅ Backup if Agmarknet key process is slow |

## 5. Satellite / Vegetation & Drought Indices (ISRO/NRSC)

| Source | What it gives | Access | Status |
|---|---|---|---|
| **NRSC NADAMS** (National Agricultural Drought Assessment and Monitoring System) | State/district/sub-district agricultural drought status, fortnightly NDVI-based | `nrsc.gov.in/Drought` — web viewer, bulletins | ⚠️ No clean public API found; likely bulletin/image scraping or manual reference for demo, not live ingestion |
| **Bhuvan / NICES** | Satellite-retrieved geophysical products (vegetation, land) | Bhuvan portal downloads | ⚠️ Same — download-based, not real-time API |
| **Google Earth Engine (MODIS NDVI, CHIRPS rainfall, soil moisture)** | Global NDVI, precipitation, soil moisture at any AOI, fully scriptable via `ee` Python/JS API | Free for research/nonprofit use, needs GCP-linked GEE account | ✅ **Recommended path** — since we're already on Google Cloud for the hackathon, GEE gives us a working real-time-ish satellite layer without fighting ISRO portal scraping. Also a strong "Google ecosystem" story for judging. |

## 6. Weather (fallback / supplementary)

| Source | What it gives | Access | Status |
|---|---|---|---|
| **OpenWeatherMap / WeatherAPI.com** | Current + forecast weather, temperature (heatwave tracking) | Free tier API key | ✅ Easy, reliable, good for heatwave/wet-bulb temperature layer to complement IMD |

## Net assessment for the hackathon build

**Tier 1 (live-API, build against directly) — status as of 2026-07-03, all confirmed working end-to-end into BigQuery:**
- ~~IMD district rainfall API~~ — dropped, no self-serve key (see above)
- Google Earth Engine (NDVI, CHIRPS precipitation, soil moisture) — ✅ live, this is now the primary current-conditions rainfall signal
- Agmarknet / data.gov.in mandi price API — ✅ live, 4,958 rows loaded (2 of 9 states pending rate-limit backfill)
- OpenWeatherMap (heat/temperature) — ✅ live, 23 rows loaded
- data.gov.in district rainfall (`6c05cd1b-ed59-40c2-bc31-e314f39c6971`) — ✅ live, 2,070 rows loaded, but demoted to historical/cross-check role, not a current-conditions source (see caveats above)

**Tier 2 (real but access is portal/bulletin/CSV, not REST — pre-scrape a snapshot dataset before the demo, refresh manually or via a scheduled scraper):**
- CWC reservoir bulletin (weekly)
- India-WRIS reservoir levels
- CGWB groundwater (quarterly — treat as static context, not a live feed)
- NRSC NADAMS drought bulletins

**Decision:** Build the live pipeline on Tier 1 sources. Pre-load Tier 2 as a seeded BigQuery table (scrape/download once, timestamp it, refresh if time allows) so the district risk model still incorporates reservoir/groundwater/drought-bulletin context without needing a live scraper to be demo-reliable. This is disclosed openly in the demo narrative ("reservoir/groundwater data refreshed weekly/quarterly by source agencies — we sync on that cadence") rather than faked as real-time.

## Sources
- [IMD API reference](https://api.imd.gov.in/public/api_reference.html)
- [data.gov.in Rainfall catalog](https://www.data.gov.in/catalog/rainfall)
- [IMD gridded rainfall](https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html)
- [India-WRIS](https://indiawris.gov.in/wris/)
- [CWC Reservoir Level & Storage Bulletin](https://cwc.gov.in/en/reservoir-level-storage-bulletin)
- [CGWB GW Data Access](https://cgwb.gov.in/GW-data-access.html)
- [Agmarknet API access](https://farmonaut.com/api-development/agmarknet-api-access-crop-prices-market-data-india)
- [data.gov.in mandi prices](https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi)
- [NRSC NADAMS](https://www.nrsc.gov.in/Drought)
- [data.gov.in APIs](https://www.data.gov.in/apis)
