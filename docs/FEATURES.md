# VanRakshak AI — 37 Required Features

This is the machine-aligned feature checklist. The live API version is available at `GET /api/features/status`.

| # | Feature | Status | Main endpoint(s) |
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

## Status meaning

- `WORKING` — implemented as a working algorithm/UI/API path.
- `WORKING_BASELINE` — working transparent baseline; future trained models can improve it.
- `WORKING_BASELINE_DEEP_MODEL_OPTIONAL` — source-backed multispectral baseline works; Open-CD is an optional validated upgrade.
- `WORKING_WITH_OPTIONAL_EE` — core path works, with additional Earth Engine layers when authenticated.
- `WORKING_WITH_AUTH_OPTIONS` — source integration works when one of the documented authorized providers is configured.
- `CREDENTIAL_GATED` — code is implemented but the external provider requires a credential.

## Non-negotiable scientific rules

- No invented accuracy, alerts, timestamps or environmental values.
- News is supporting context, not proof of causation.
- Roads/mines/settlements are contextual evidence, not proof of illegal activity.
- Carbon is an estimate with uncertainty, not a field inventory.
- SoilGrids values are modelled reference estimates, not soil samples.
- Risk/prediction outputs are labelled estimates.
- Satellite "live" means newest available observations, not continuous video.
