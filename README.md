# 🌿 VanRakshak AI

**India-first satellite forest intelligence and early-warning command center.**

VanRakshak AI combines Earth-observation catalogues, forest alerts, weather, fire, soil, human-pressure, protected-area and news/context signals into a single explainable workflow for forest monitoring and investigation.

> This repository is designed to never fabricate environmental observations. External sources that require credentials are reported as **not configured** until the appropriate key/token is supplied.

## What works in this build

- India-first MapLibre command-center UI.
- Dynamic Earth-data layer/filter registry covering satellite, forest, vegetation, fire, climate, drought, soil, terrain, human pressure, conservation and carbon.
- Copernicus Data Space STAC search for recent Sentinel-2 L2A scene metadata.
- Open-Meteo current/forecast weather + soil-moisture variables.
- SoilGrids point soil-property integration.
- OpenStreetMap Overpass human-pressure search.
- NASA FIRMS VIIRS NOAA-21 NRT fire adapter when `FIRMS_MAP_KEY` is configured.
- Protected Planet v4 adapter when `PROTECTED_PLANET_TOKEN` is configured.
- GDELT recent forest-related news/context adapter.
- Multi-source deep-region investigation endpoint.
- Explainable warning/risk engine.
- Threat cascade engine.
- Forest resilience estimate.
- What-if simulation.
- Carbon-loss estimator with uncertainty range.
- Patrol-point prioritization/route ordering baseline.
- Natural-language-to-structured Earth filter parser.
- Automatic PDF investigation report generation.
- API provenance/freshness labels and graceful source failures.
- 37-feature product registry.

## Important production boundaries

A few parts require deployment credentials or trained model artefacts:

- **NASA FIRMS:** free MAP key.
- **Protected Planet:** API v4 token.
- **Google Earth Engine / Dynamic World direct API:** Google Cloud/Earth Engine project authentication if you enable a direct EE adapter.
- **Sentinel imagery pixels / on-map multispectral rendering:** connect a sanctioned download/processing route (Copernicus/Sentinel Hub/ODC-STAC) and tile generated COGs with TiTiler. This repository already provides the catalogue and layer architecture; large raster processing belongs in workers.
- **Open-CD production deforestation model:** train/evaluate against a geographic holdout set and place the selected model checkpoint in your deployment. Do not publish fake accuracy.
- **Road-network patrol routing:** the included baseline works without a routing server; integrate GraphHopper/OR-Tools for actual road/track routing.

## Quick start

```bash
cd vanrakshak-ai
cp .env.example .env
cd backend
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Open: `http://localhost:8000`

API docs: `http://localhost:8000/docs`

### Run tests

```bash
cd vanrakshak-ai
PYTHONPATH=backend pytest -q backend/tests
```

### Docker

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up --build
```

## Core endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Runtime health |
| `GET /api/features` | All 37 required features |
| `GET /api/layers` | Layer/filter registry |
| `GET /api/satellite/latest` | Latest Sentinel-2 L2A catalogue scenes |
| `GET /api/weather` | Open-Meteo weather/environment |
| `GET /api/soil` | SoilGrids properties |
| `GET /api/fire` | NASA FIRMS fire detections |
| `GET /api/human-pressure` | OSM/Overpass roads/settlements/industry |
| `GET /api/news` | GDELT contextual news |
| `GET /api/investigate` | Multi-source region investigation |
| `POST /api/intelligence/risk` | Explainable warning/priority score |
| `POST /api/intelligence/cascade` | Threat cascade |
| `POST /api/intelligence/resilience` | Forest resilience estimate |
| `POST /api/intelligence/what-if` | Scenario simulation |
| `POST /api/intelligence/intervention` | Intervention suggestions |
| `POST /api/carbon` | Carbon-impact estimate |
| `POST /api/patrol` | Patrol ordering baseline |
| `GET /api/query` | Natural-language filter parsing |
| `POST /api/report` | PDF report |

## Data-quality labels

VanRakshak separates data into:

- `LIVE_NRT`
- `DYNAMIC_RECENT`
- `HISTORICAL`
- `REFERENCE`
- `FORECAST`
- `AI_ESTIMATE`

A delayed satellite image is **never** labelled as continuous live video.

## Architecture

```text
Copernicus / ASF / GFW / FIRMS / Open-Meteo / SoilGrids / OSM / GDELT
                              ↓
                      Provider adapters
                              ↓
                   Validation + provenance
                              ↓
                PostGIS / PgSTAC / cache layer
                              ↓
              Raster/vector + AI intelligence layer
                              ↓
                         FastAPI
                              ↓
                  MapLibre command center
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/FEATURES.md`](docs/FEATURES.md) and [`docs/SOURCES.md`](docs/SOURCES.md).

## License

MIT for this repository's original code. External datasets/APIs retain their own terms and attribution requirements.
