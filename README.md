# 🌿 VanRakshak AI — Satellite Forest Intelligence Command Center

**VanRakshak AI** is an India-first forest monitoring, investigation and early-warning platform for the DATUM Hackathon climate/environment problem **Satellite-Based Deforestation Monitoring**.

The system combines real Earth-observation catalogues, Sentinel imagery, forest alerts, multispectral analysis, weather/climate, fire, soil, terrain, protected-area context, human-pressure evidence, news context and explainable intelligence in one map-first command center.

> **Data integrity rule:** VanRakshak never substitutes fabricated environmental values when a provider is unavailable. Every source-backed value retains provenance/freshness, and predictions are labelled as estimates rather than facts.

## Current build

- **37/37 requested product capabilities have implementation paths and API/UI hooks.**
- **Real Sentinel-2 catalogue + visual tiles** through Copernicus Data Space and Element 84 Earth Search.
- **Sentinel-1 search** through ASF for radar-scene availability.
- **True color / false color / NDVI / NDMI / NBR / NDWI** map modes through TiTiler STAC rendering.
- **Before ↔ After comparison** with synchronized real scenes and split-slider UI.
- **Forest Time Machine** over historical Sentinel-2 observations.
- **Remote change analysis** using cloud-masked multispectral Sentinel-2 pixels, forest-conditioned vegetation decline, fragmentation metrics and anomaly corroboration.
- **Earth Engine layer catalogue** for Dynamic World, Hansen loss, SRTM terrain, JRC water, MODIS LST/burned area, CHIRPS rainfall, GEDI biomass, population/human-modification and protected areas when authenticated.
- **Global Forest Watch integrated-alert tiles** with date/confidence filtering.
- **NASA FIRMS NRT fire adapter**, **Open-Meteo**, **SoilGrids**, **OSM/Overpass**, **Protected Planet**, **GDELT**, **ISRO Bhuvan**, and **MOSDAC integration helpers**.
- **Forest Digital Profile**, **Evidence Chain**, **AI Forest Doctor**, **smart warning**, **threat cascade**, **resilience/recovery**, **threat projection**, **what-if simulation**, **regional comparison**, **climate–forest correlation**, **carbon estimate**, **patrol routing**, **automatic PDF report**.
- **PostGIS persistence**, **Redis/Celery workers**, **TiTiler**, Docker Compose and GitHub Actions CI.

## 37 feature implementation matrix

| # | Capability | Runtime status | Main endpoint(s) |
|---:|---|---|---|
| 1 | Real Satellite Monitoring | `WORKING` | /api/satellite/latest<br>/api/map/satellite-layer |
| 2 | Forest Cover Monitoring | `WORKING_WITH_OPTIONAL_EE` | /api/layers<br>/api/earth-engine/layer/dynamic_world_trees |
| 3 | AI Deforestation Detection | `WORKING_BASELINE_DEEP_MODEL_OPTIONAL` | /api/analysis/remote-change<br>/api/ai/change-model/status |
| 4 | Before–After Satellite Comparison | `WORKING` | /api/map/compare<br>/api/analysis/remote-change |
| 5 | Multi-Spectral Analysis | `WORKING` | /api/map/satellite-layer<br>/api/analysis/remote-change |
| 6 | Multi-Layer Earth Map | `WORKING` | /api/layers<br>/api/map/gfw-layer<br>/api/earth-engine/layer/{layer_id}<br>/api/bhuvan/tile/{z}/{x}/{y}.png |
| 7 | Deep Region Investigation | `WORKING` | /api/investigate<br>/api/analysis/evidence-chain |
| 8 | Temperature Intelligence | `WORKING` | /api/weather<br>/api/climate/anomaly |
| 9 | Weather Intelligence | `WORKING` | /api/weather |
| 10 | Drought & Water Stress | `WORKING` | /api/climate/anomaly<br>/api/weather<br>/api/earth-engine/layer/jrc_water_occurrence |
| 11 | Fire & Heat Detection | `CREDENTIAL_GATED` | /api/fire<br>/api/earth-engine/layer/modis_burned_area |
| 12 | Vegetation Health | `WORKING` | /api/analysis/vegetation-series<br>/api/map/satellite-layer?mode=ndvi |
| 13 | Environmental Anomaly Radar | `WORKING` | /api/intelligence/anomaly-radar<br>/api/climate/anomaly |
| 14 | AI Forest Doctor | `WORKING` | /api/intelligence/forest-doctor<br>/api/analysis/evidence-chain |
| 15 | Smart Warning System | `WORKING` | /api/intelligence/risk<br>/api/analysis/evidence-chain |
| 16 | Threat Prediction | `WORKING_BASELINE` | /api/intelligence/predict<br>/api/intelligence/predict-location |
| 17 | Threat Cascade Engine | `WORKING` | /api/intelligence/cascade |
| 18 | AI Priority Engine | `WORKING` | /api/intelligence/risk<br>/api/intelligence/compare-regions |
| 19 | Investigation/Patrol Optimizer | `WORKING` | /api/patrol<br>/api/patrol/road-route |
| 20 | AI What-If Simulator | `WORKING` | /api/intelligence/what-if |
| 21 | Intervention Engine | `WORKING` | /api/intelligence/intervention |
| 22 | Recovery Intelligence | `WORKING` | /api/intelligence/recovery<br>/api/analysis/recovery-location |
| 23 | Recovery Exit Conditions | `WORKING` | /api/intelligence/recovery<br>/api/analysis/recovery-location |
| 24 | Forest Resilience Score | `WORKING` | /api/intelligence/resilience |
| 25 | Protected Area Intelligence | `WORKING_WITH_AUTH_OPTIONS` | /api/protected-areas<br>/api/earth-engine/value/wdpa_protected |
| 26 | Forest Fragmentation Analysis | `WORKING` | /api/analysis/fragmentation<br>/api/analysis/remote-change |
| 27 | Carbon Loss Calculator | `WORKING` | /api/carbon<br>/api/analysis/evidence-chain |
| 28 | Climate–Forest Correlation | `WORKING` | /api/intelligence/correlation<br>/api/analysis/climate-forest-correlation |
| 29 | AI Evidence Chain | `WORKING` | /api/analysis/evidence-chain |
| 30 | Explainable AI | `WORKING` | /api/intelligence/risk<br>/api/analysis/evidence-chain |
| 31 | Natural-Language Earth Query | `WORKING` | /api/query |
| 32 | Automatic Investigation Report | `WORKING` | /api/report<br>/api/report/investigation |
| 33 | Regional Threat Comparison | `WORKING` | /api/intelligence/compare-regions |
| 34 | Forest Time Machine | `WORKING` | /api/time-machine |
| 35 | Live Command Center | `WORKING` | /<br>/api/health |
| 36 | Forest Digital Profile | `WORKING` | /api/forest-profile |
| 37 | News & Internet Intelligence | `WORKING` | /api/news<br>/api/analysis/evidence-chain |

Statuses such as `CREDENTIAL_GATED` are intentional: the integration code exists, but the external provider legally/technically requires a user-owned credential. A missing credential is shown as unavailable rather than replaced with fake data.

## Quick start

### Local API + dashboard

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000` and API docs at `http://localhost:8000/docs`.

### Production-style Docker stack

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up --build
```

Services:

- API/dashboard: `http://localhost:8000`
- TiTiler: `http://localhost:8001`
- PostgreSQL/PostGIS: `localhost:5432`
- Redis: `localhost:6379`
- Celery worker + beat scheduler run inside Compose.

## Credentials you must provide for the corresponding providers

```env
FIRMS_MAP_KEY=
PROTECTED_PLANET_TOKEN=
GOOGLE_CLOUD_PROJECT=
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

- **FIRMS_MAP_KEY** — enables NASA FIRMS near-real-time fire points.
- **PROTECTED_PLANET_TOKEN** — enables Protected Planet API v4.
- **Earth Engine credentials/project** — enables Dynamic World, Hansen, GEDI, SRTM, MODIS, CHIRPS, WDPA and other Google Earth Engine filters.
- **MOSDAC downloads** — use the official authenticated `mdapi` workflow; credentials are never committed to Git.
- **Google Earth Engine client** — official repository: https://github.com/google/earthengine-api
- **Secret handling** — never commit real provider keys to this public repository. See `docs/SECRETS_SETUP.md`.

## Main operational APIs

```text
GET  /api/health
GET  /api/source-health
GET  /api/features/status
GET  /api/layers
GET  /api/geocode
GET  /api/satellite/latest
GET  /api/satellite/sentinel1
GET  /api/map/satellite-layer
GET  /api/map/compare
GET  /api/map/gfw-layer
GET  /api/time-machine
GET  /api/earth-engine/catalog
GET  /api/earth-engine/layer/{layer_id}
GET  /api/bhuvan/info
GET  /api/mosdac/info
GET  /api/weather
GET  /api/climate/anomaly
GET  /api/soil
GET  /api/fire
GET  /api/human-pressure
GET  /api/news
GET  /api/investigate
GET  /api/forest-profile
GET  /api/analysis/remote-change
GET  /api/analysis/evidence-chain
GET  /api/analysis/vegetation-series
GET  /api/analysis/recovery-location
GET  /api/analysis/climate-forest-correlation
POST /api/analysis/fragmentation
POST /api/intelligence/risk
POST /api/intelligence/forest-doctor
POST /api/intelligence/cascade
POST /api/intelligence/what-if
POST /api/intelligence/predict
GET  /api/intelligence/predict-location
POST /api/patrol/road-route
GET  /api/report/investigation
```

## Change-detection policy

VanRakshak has a **working source-backed multispectral baseline**. It does not claim a fake deep-learning accuracy. The optional Open-CD runtime is activated only when a real config/checkpoint has been trained and validated.

Recommended evaluation before presenting a trained model:

```text
Geographic holdout split
Precision
Recall
F1
IoU / Dice
False-positive rate
Inference time
Cloud/season robustness
```

See `ai/opencd/README.md` for the deep-model handoff.

## Data classes shown in the platform

- `LIVE_NRT`
- `DYNAMIC_RECENT`
- `HISTORICAL`
- `REFERENCE`
- `FORECAST`
- `AI_ESTIMATE`

A Sentinel scene is never described as continuous "live video". Capture timestamps and data-source freshness remain visible.

## Validation

```bash
PYTHONPATH=backend pytest -q backend/tests
PYTHONPATH=backend python -m compileall -q backend/app
node --check web/app.js
```

## Documentation

- `docs/ARCHITECTURE.md`
- `docs/FEATURES.md`
- `docs/SOURCES.md`
- `docs/DEPLOYMENT.md`
- `docs/SECRETS_SETUP.md`
- `docs/OPENCODE_INSTRUCTIONS.md`
- `docs/HERMES_INSTRUCTIONS.md`

## License

Original repository code is MIT licensed. Every external API/dataset keeps its own terms, attribution and access requirements.
