# OPENCODE INSTRUCTION FILE — VANRAKSHAK AI

You are the PRIMARY IMPLEMENTATION ENGINEER for VanRakshak AI.

Your responsibility is to create and maintain the production-style codebase described below. You own architecture, code quality, integration, testing and implementation. Work incrementally. Do not attempt to generate the entire platform in one untested pass.


# VANRAKSHAK AI — MASTER PROJECT SPECIFICATION

## Mission
Build an India-first, satellite-driven forest intelligence and early-warning platform. VanRakshak AI must detect, verify, explain, prioritize and predict forest/environmental threats and convert raw Earth-observation data into practical investigation and intervention workflows.

The project is for a climate/environment hackathon and must be treated as a serious working prototype, not a static UI mockup.

## Core principles
- REAL DATA FIRST. Never fabricate API values, timestamps, model metrics, satellite observations, alerts or reports.
- PROVENANCE FIRST. Every dashboard value must expose source, timestamp, resolution/freshness when relevant.
- INDIA FIRST. Start with a complete India map and support state → district → forest/protected-area drill-down.
- MAP FIRST. The main experience is a large interactive map, not a grid of cards.
- CLEAN UI. Avoid congestion. Put advanced controls in collapsible panels/tabs/drawers.
- MODULAR. External providers must be isolated behind adapters.
- RESILIENT. One provider failure must not crash the whole dashboard.
- EXPLAINABLE. Every AI risk/alert must explain its evidence.
- HONEST FRESHNESS. Sentinel imagery is not continuous live video; display actual capture time. Use 'live/NRT' only for feeds that truly qualify.
- TEST EVERYTHING. No phase is complete until unit/integration tests and basic end-to-end validation pass.

## Main UI concept
- Large India satellite/forest map as the primary canvas.
- Left navigation: Map, Forest Cover, Alerts, Analysis, Weather, Fire & Heat, Soil & Terrain, Predictions, Patrol Planner, Reports.
- Top search: state/district/forest/coordinates/natural-language query.
- Quick map tabs: Satellite, Forest, Climate, Threats, + Layers.
- Right-side context panel appears only after a region/hotspot is selected.
- Bottom analytics area only for the most important trend graphs; keep it collapsible.
- Use dark cinematic styling, forest green accents, red/orange only for threats.
- Do NOT reproduce the earlier congested layout; preserve whitespace and map visibility.

## 37 REQUIRED FEATURES
1. 🛰️ Real Satellite Monitoring — Real Sentinel-2/GFW and other supported observations; update when new imagery/data becomes available. Always display source timestamp and freshness.
2. 🌳 Forest Cover Monitoring — Track forest extent, canopy condition and forest-loss changes across any selected region.
3. 🔴 AI Deforestation Detection — Detect canopy loss and return exact affected polygon/mask, hectares, severity and confidence.
4. 🔄 Before–After Satellite Comparison — Date-based split slider with aligned imagery and synchronized zoom.
5. 🌈 Multi-Spectral Analysis — True color, false color, NDVI, NDMI/moisture, NBR/burn, NDWI/water and other appropriate bands/indices.
6. 🗺️ Multi-Layer Earth Map — One interactive India-first map combining satellite, forest, weather, temperature, fire, risk, soil, terrain, protected areas and carbon.
7. 🔍 Deep Region Investigation — Drill India → state → district → forest/protected area → disturbance polygon.
8. 🌡️ Temperature Intelligence — Latest temperature, historical trend and temperature anomaly.
9. ☁️ Weather Intelligence — Rainfall, humidity, wind, cloud cover and forecast for selected forest region.
10. 🌧️ Drought & Water Stress — Rainfall deficit, soil moisture, evapotranspiration and environmental dryness indicators.
11. 🔥 Fire & Heat Detection — NASA FIRMS/other supported thermal sources; active fires, heat signals, burn history and risk.
12. 🌿 Vegetation Health — NDVI and related vegetation indicators, trend and condition class.
13. 📡 Environmental Anomaly Radar — Detect unusual combinations of forest, climate, weather, fire and vegetation signals.
14. 🧠 AI Forest Doctor — Diagnose probable causes of deterioration by fusing satellite, weather, fire, road/settlement, soil, land-cover and news evidence.
15. 🚨 Smart Warning System — Normal / Watch / Warning / Critical with transparent thresholds and confidence.
16. 🔮 Threat Prediction — Predict future vulnerability/risk regions; label outputs as risk estimates, not certainty.
17. 🕸️ Threat Cascade Engine — Model chains such as heat → drought → vegetation stress → fire → canopy loss.
18. 🎯 AI Priority Engine — Rank detected threats by severity, confidence, protected status, ecological impact, recency and accessibility.
19. 🚁 Investigation/Patrol Optimizer — Optimize route/order for multiple high-priority alerts using road/track networks.
20. 🧪 AI What-If Simulator — Recalculate risk under changed temperature, rainfall, fire frequency or continued clearing assumptions.
21. 🛡️ Intervention Engine — Suggest where intervention could deliver the greatest potential environmental benefit and why.
22. 🌱 Recovery Intelligence — Track whether disturbed forest is deteriorating, stable or recovering.
23. 🟢 Recovery Exit Conditions — Define measurable requirements for moving Critical/Warning → Watch/Normal.
24. 🌲 Forest Resilience Score — Composite estimate of ability to withstand climate/environmental stress with explainable components.
25. 🏞️ Protected Area Intelligence — Detect disturbances inside/near protected forests, wildlife sanctuaries and conservation zones.
26. 🧩 Forest Fragmentation Analysis — Patch count, edge density, core forest, connectivity and fragmentation changes.
27. 🧮 Carbon Loss Calculator — Estimate biomass/carbon impact with ranges, source and uncertainty.
28. 📊 Climate–Forest Correlation — Show relationships among rainfall, temperature, vegetation, fire and forest loss over time.
29. 🕵️ AI Evidence Chain — Connect satellite evidence, spectral change, radar confirmation, climate, fire, land use and historical events for each alert.
30. 🤖 Explainable AI — Show exactly why an alert/risk score was produced; never show an unexplained number.
31. 💬 Natural-Language Earth Query — Example: 'Show forests in Karnataka with high heat and recent canopy loss'; convert language to structured geospatial filters/queries.
32. 📄 Automatic Investigation Report — Generate a report with location, source timestamps, before/after evidence, conditions, carbon impact, risk and recommended action.
33. 🌐 Regional Threat Comparison — Compare forests/states and identify where conditions are changing fastest using normalized metrics.
34. 📈 Forest Time Machine — Explore historical observations and animate forest/environmental change through time.
35. 🚨 Live Command Center — Clean cinematic dashboard containing map, alerts, investigation, graphs, data-source status and AI health without congestion.
36. 🌍 Forest Digital Profile — A click-to-open health record for any forest: type, extent, canopy, NDVI, weather, soil, terrain, fire history, roads, settlements, protected status, carbon, fragmentation, risk and recovery.
37. 📰 News & Internet Intelligence — For each hotspot, search recent local/regional reports and return relevant articles as supporting context with title, date, publisher and URL; never treat news correlation as proof of causation.

## EARTH ENGINE / MAP FILTER & LAYER SYSTEM

The dashboard MUST use a clean collapsible layer drawer rather than placing dozens of controls directly on the map.

### Top-level quick tabs
- Satellite
- Forest
- Climate
- Threats
- + Layers

### Layer categories
1. Satellite Imagery
   - Sentinel-2 Optical
   - Sentinel-1 Radar
   - Landsat
   - MODIS / NASA GIBS
   - True Color
   - False Color
   - Historical imagery
2. Forest
   - Forest cover
   - Tree canopy %
   - Forest loss
   - Forest gain
   - Biomass
   - Disturbance alerts
   - Fragmentation
3. Vegetation
   - NDVI
   - NDMI / moisture
   - NBR / burn
   - NDWI / water
   - Productivity / vegetation condition
4. Fire
   - Active fires
   - Heat hotspots
   - Burned area
   - Fire history
   - Fire risk
5. Climate & Weather
   - Temperature
   - Surface temperature where suitable
   - Rainfall
   - Humidity
   - Wind
   - Cloud cover
   - Forecast
   - Temperature anomaly
   - Rainfall anomaly
6. Water & Drought
   - Soil moisture
   - Drought
   - Water stress
   - Surface water
   - Evapotranspiration
   - Precipitation
7. Soil
   - Soil type
   - pH
   - Organic carbon
   - Nitrogen
   - Clay
   - Sand
   - Silt
   - Bulk density
   - CEC / fertility proxy
8. Terrain
   - Elevation / DEM
   - Slope
   - Aspect
   - Erosion susceptibility
9. Land Cover
   - Forest
   - Cropland
   - Grassland
   - Shrubland
   - Built-up
   - Bare land
   - Water
10. Human Pressure
   - Roads/tracks
   - Settlements
   - Construction
   - Industrial/quarry/mine features where mapped
   - Population / human modification
11. Conservation
   - Protected areas
   - Wildlife zones / sanctuaries
   - Eco-sensitive zones when available
12. Carbon / Biomass
   - Biomass density
   - Estimated stored carbon
   - Estimated carbon loss

### Global filters
- Date / date range
- Today / 7 days / 30 days / 1 year / custom
- Data source
- Resolution: <=10 m / 10–30 m / 30–250 m / 250 m–1 km
- Freshness: Live/NRT / Latest / Historical / Forecast / Prediction
- State
- District
- Forest / protected area
- Confidence threshold
- Alert severity
- Cloud-cover threshold
- Protected-area only toggle

### Data status badges
Every layer/value MUST be labeled as one of:
- LIVE / NRT
- DYNAMIC / RECENT
- HISTORICAL
- REFERENCE
- FORECAST
- AI ESTIMATE

Never call delayed satellite imagery 'live'. Always show capture time, source and latest sync time.

## APPROVED REPOS / APIS / DATA SOURCES

### Satellite ingestion / catalogues
- EODAG — https://github.com/CS-SI/eodag
- PySTAC Client — https://github.com/stac-utils/pystac-client
- ODC-STAC — https://github.com/opendatacube/odc-stac
- Sentinel Hub Python — https://github.com/sentinel-hub/sentinelhub-py
- ASF Search (Sentinel-1) — https://github.com/asfadmin/Discovery-asf_search
- Copernicus Browser — https://github.com/eu-cdse/copernicus-browser
- Copernicus Data Space STAC — https://documentation.dataspace.copernicus.eu/APIs/STAC.html
- ISRO MOSDAC — https://mosdac.gov.in/
- MOSDAC Download API — https://mosdac.gov.in/downloadapi-manual
- NASA GIBS API — https://nasa-gibs.github.io/gibs-api-docs/
- NASA Worldview — https://github.com/nasa-gibs/worldview
- NASA GIBS web examples — https://github.com/nasa-gibs/gibs-web-examples

### Forest / land cover / validation
- Dynamic World — https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1
- Hansen Global Forest Change — https://developers.google.com/earth-engine/datasets/catalog/UMD_hansen_global_forest_change_2025_v1_13
- Global Forest Watch — https://www.globalforestwatch.org/
- GFW GitHub — https://github.com/wri/gfw
- GFW Data API — https://github.com/wri/gfw-data-api
- GFW API examples — https://github.com/wri/data-api-examples
- GFW Tiles — https://tiles.globalforestwatch.org/
- Forest Watcher — https://github.com/forest-watcher/forest-watcher

### AI change detection / geospatial foundation models
- Open-CD — https://github.com/likyoo/open-cd
- RSChange — https://github.com/xwmaxwma/rschange
- TorchGeo — https://github.com/microsoft/torchgeo
- TerraTorch — https://github.com/IBM/terratorch
- NASA Prithvi EO 2.0 — https://github.com/NASA-IMPACT/Prithvi-EO-2.0
- Clay Foundation Model — https://github.com/Clay-foundation/model
- SamGeo / Segment-Geospatial — https://github.com/opengeos/segment-geospatial

### Preprocessing / raster / vector
- s2cloudless — https://github.com/sentinel-hub/sentinel2-cloud-detector
- eo-learn — https://github.com/sentinel-hub/eo-learn
- Rasterio — https://github.com/rasterio/rasterio
- GeoPandas — https://github.com/geopandas/geopandas
- xarray — https://github.com/pydata/xarray
- rio-cogeo — https://github.com/cogeotiff/rio-cogeo
- rio-tiler — https://github.com/cogeotiff/rio-tiler
- Sentinel Hub custom scripts — https://github.com/sentinel-hub/custom-scripts
- geemap — https://github.com/gee-community/geemap

### Fire / weather / drought / soil
- NASA FIRMS — https://firms.modaps.eosdis.nasa.gov/
- FIRMS API — https://firms.modaps.eosdis.nasa.gov/api/
- FIRMS WMS — https://firms.modaps.eosdis.nasa.gov/mapserver/wms-info/
- Open-Meteo — https://open-meteo.com/
- Open-Meteo Historical API — https://open-meteo.com/en/docs/historical-weather-api
- Open-Meteo ECMWF API — https://open-meteo.com/en/docs/ecmwf-api
- SoilGrids — https://soilgrids.org/
- SoilGrids docs — https://docs.isric.org/globaldata/soilgrids/

### India-specific GIS
- ISRO Bhuvan — https://bhuvan.nrsc.gov.in/
- Bhuvan services — https://bhuvan.nrsc.gov.in/bhuvan_links.php
- NRSC — https://www.nrsc.gov.in/
- MOSDAC — https://mosdac.gov.in/

### Protected areas / roads / human pressure / news
- Protected Planet API — https://api.protectedplanet.net/documentation
- OpenStreetMap — https://www.openstreetmap.org/
- Overpass API — https://wiki.openstreetmap.org/wiki/Overpass_API
- Overpass Turbo — https://overpass-turbo.eu/
- GDELT — https://www.gdeltproject.org/
- GDELT DOC API — https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

### Carbon / fragmentation / risk / explainability
- NASA GEDI — https://gedi.umd.edu/
- NASA Earthdata Search — https://search.earthdata.nasa.gov/
- PyLandStats — https://github.com/martibosch/pylandstats
- XGBoost — https://github.com/dmlc/xgboost
- SHAP — https://github.com/shap/shap
- scikit-learn — https://github.com/scikit-learn/scikit-learn
- NetworkX — https://github.com/networkx/networkx

### Patrol routing
- GraphHopper — https://github.com/graphhopper/graphhopper
- Google OR-Tools — https://github.com/google/or-tools
- OSRM — https://github.com/Project-OSRM/osrm-backend

### Frontend maps / charts
- MapLibre GL JS — https://github.com/maplibre/maplibre-gl-js
- deck.gl — https://github.com/visgl/deck.gl
- Leafmap — https://github.com/opengeos/leafmap
- Apache ECharts — https://github.com/apache/echarts
- Plotly.js — https://github.com/plotly/plotly.js

### Raster tile serving / geospatial backend
- TiTiler — https://github.com/developmentseed/titiler
- FastAPI — https://github.com/fastapi/fastapi
- PostGIS — https://github.com/postgis/postgis
- PostgreSQL — https://www.postgresql.org/
- PgSTAC — https://github.com/stac-utils/pgstac
- Celery — https://github.com/celery/celery
- Redis — https://github.com/redis/redis

### Reporting / annotation / experiment tracking
- WeasyPrint — https://github.com/Kozea/WeasyPrint
- ReportLab mirror — https://github.com/MrBitBucket/reportlab-mirror
- CVAT — https://github.com/cvat-ai/cvat
- MLflow — https://github.com/mlflow/mlflow
- DVC — https://github.com/iterative/dvc

## Suggested common data contract
All external adapters should normalize toward a consistent structure, for example:
```json
{
  "source": "NASA FIRMS",
  "dataset_id": "VIIRS_SNPP_NRT",
  "observed_at": "ISO-8601",
  "fetched_at": "ISO-8601",
  "freshness": "NRT",
  "resolution_m": null,
  "geometry": {},
  "properties": {},
  "quality": {},
  "provenance_url": "https://..."
}
```

## Core technical architecture
```text
Satellite/Data Providers
        ↓
Provider Adapters
        ↓
Validation + caching + provenance
        ↓
PostGIS / PgSTAC / object storage
        ↓
Raster/vector preprocessing
        ↓
Open-CD / risk models / environmental fusion
        ↓
FastAPI
        ↓
TiTiler + vector APIs
        ↓
MapLibre + deck.gl + ECharts
        ↓
VanRakshak Command Center
```

## AI architecture
- Main deforestation/change model: benchmark Open-CD models such as TinyCD / Changer / ChangeFormer.
- Baseline: NDVI/NDMI/NBR threshold-based change detector.
- Validate model against geographic holdout regions, not only random patch splits.
- Evaluate Precision, Recall, F1, IoU, Dice, false-positive rate and inference time.
- Risk/prediction model: XGBoost or equivalent interpretable tabular model.
- Explainability: SHAP.
- Threat cascade: NetworkX/state graph.
- Foundation models Prithvi/Clay/TerraTorch are advanced experiments AFTER the core pipeline works.
- No invented accuracy. Store real experiment metrics with MLflow.

## Hotspot investigation workflow
When user clicks an alert:
1. Resolve state/district/forest/protected-area context.
2. Load current and previous satellite observations.
3. Show before/after slider.
4. Show forest loss polygon and hectares.
5. Calculate NDVI/NDMI/NBR changes.
6. Check Sentinel-1/radar confirmation where possible.
7. Check GFW/Dynamic World/Hansen evidence where relevant.
8. Check FIRMS fire evidence.
9. Load current/historical weather, rainfall and soil moisture.
10. Load SoilGrids properties.
11. Check roads/tracks/settlements/human pressure with OSM/Overpass.
12. Check Protected Planet/Bhuvan conservation status.
13. Estimate fragmentation change with PyLandStats.
14. Estimate biomass/carbon impact with suitable biomass data such as GEDI, showing uncertainty.
15. Search GDELT/relevant public sources for related recent news.
16. Run probable-driver analysis.
17. Generate explainable warning/priority score.
18. Offer patrol route.
19. Generate investigation report.

## Evidence / cause rules
- Probable cause != proven cause.
- A news article is contextual evidence, not proof.
- A nearby road is a risk/context factor, not proof of logging.
- Fire correlation must show time/distance.
- Carbon values must be estimates/ranges.
- SoilGrids values are modeled estimates, not field samples.
- Predictions must be labeled predictions/risk estimates.

## Quality gates
- No hard-coded fake data in production paths.
- Mock fixtures allowed only in tests/dev and must be clearly marked.
- Environment variables for all keys/secrets.
- API timeouts/retries.
- Cache external requests.
- Graceful fallback when sources are unavailable.
- Source attribution everywhere.
- Logs for ingestion/model failures.
- Docker Compose for reproducible local start.


## YOUR ROLE — OPENCODE

### You own
- monorepo creation
- frontend
- backend
- database schema
- provider adapters
- geospatial processing
- AI training/inference integration
- scheduled workers
- caching
- authentication/config where needed
- tests
- Docker
- documentation
- API contracts
- report generation
- integration of specifications produced by Hermes

### You do NOT do blindly
- Do not randomly clone every listed repository.
- Do not paste third-party code without checking license/API compatibility.
- Do not run several agents against the same files concurrently.
- Do not claim an integration works until it has been tested.
- Do not hide broken sources behind fake fallback numbers.

## Preferred monorepo
```text
vanrakshak-ai/
├─ apps/
│  ├─ web/                 # Next.js/React UI
│  └─ api/                 # FastAPI
├─ services/
│  ├─ ingestion/
│  ├─ ai-inference/
│  ├─ report-generator/
│  └─ scheduler/
├─ packages/
│  ├─ ui/
│  ├─ map/
│  ├─ layer-registry/
│  ├─ api-client/
│  └─ shared-types/
├─ adapters/
│  ├─ copernicus/
│  ├─ sentinel1_asf/
│  ├─ mosdac/
│  ├─ gfw/
│  ├─ firms/
│  ├─ openmeteo/
│  ├─ soilgrids/
│  ├─ bhuvan/
│  ├─ protectedplanet/
│  ├─ overpass/
│  ├─ gdelt/
│  └─ gedi/
├─ geospatial/
│  ├─ raster/
│  ├─ vector/
│  ├─ indices/
│  ├─ fragmentation/
│  └─ tiles/
├─ ai/
│  ├─ change_detection/
│  ├─ risk/
│  ├─ explainability/
│  ├─ cascade/
│  └─ evaluation/
├─ db/
│  ├─ migrations/
│  ├─ seed/
│  └─ schemas/
├─ workers/
├─ tests/
├─ infra/
│  ├─ docker/
│  └─ compose/
├─ docs/
└─ .env.example
```

## Frontend requirements
- Next.js/React + TypeScript.
- MapLibre GL JS is primary map.
- deck.gl for high-volume alerts/heatmaps/advanced overlays.
- ECharts for analytics.
- Layer registry must drive UI automatically.
- URL state should preserve selected region, layer set and date range when practical.
- Before/after split comparison must synchronize pan/zoom.
- Right investigation panel must use tabs: Overview / Before-After / Analysis / Environmental / News & Evidence.
- Map remains the visual priority.
- Responsive enough for common laptop demo resolutions.

## Backend requirements
- FastAPI.
- PostgreSQL + PostGIS.
- PgSTAC where helpful.
- Redis + Celery for scheduled/long-running jobs.
- TiTiler/rio-tiler for raster tile delivery.
- Strict Pydantic schemas.
- Store data source + timestamps + quality metadata.
- Separate ingestion data from AI-derived data.
- Add health endpoints for every external dependency.

## Layer registry requirement
Create a machine-readable layer registry. Example:
```json
{
  "id": "ndvi",
  "label": "NDVI",
  "category": "vegetation",
  "source": "sentinel-2",
  "render_type": "raster",
  "freshness": "latest",
  "unit": "index",
  "supports_time": true,
  "supports_opacity": true,
  "legend": true
}
```
The frontend must render the filter/layer drawer from this registry instead of hard-coding controls.

## API adapter standard
Each adapter should implement a predictable contract such as:
- search(aoi, start, end, filters)
- latest(aoi)
- fetch(...)
- normalize(...)
- health()
- metadata()

Each adapter MUST report:
- provider
- dataset
- observation timestamp
- fetch timestamp
- spatial resolution if known
- quality/cloud/confidence fields
- source URL
- license/attribution note where relevant

## Implementation phases

### PHASE 0 — Bootstrap
- Create monorepo.
- Docker Compose: web, api, postgres/postgis, redis.
- .env.example.
- lint/format/test setup.
- CI.
- README architecture diagram.
STOP if base stack does not boot cleanly.

### PHASE 1 — India Map + Layer Framework
- India-focused MapLibre map.
- state/district boundaries where a reliable source is available.
- search/geocoding interface.
- dynamic layer drawer.
- date/source/resolution/freshness filters.
- clean non-congested layout.
- basic PostGIS.
- no AI yet.
PASS CRITERIA: map loads, filters work, state selection works, layer registry is testable.

### PHASE 2 — Live/Recent Data Sources
Implement one at a time:
1. Open-Meteo
2. NASA FIRMS
3. Copernicus/STAC Sentinel-2
4. ASF/Sentinel-1
5. GFW
6. Dynamic World/EE where credentials allow
7. SoilGrids
8. Protected Planet
9. OSM/Overpass
10. MOSDAC/Bhuvan where access allows
11. GDELT
12. GEDI
For every adapter: integration test + graceful failure.
PASS CRITERIA: selected region loads actual source-backed data and timestamps.

### PHASE 3 — Satellite Processing
- cloud masking
- band selection
- NDVI, NDMI, NBR, NDWI
- COG generation
- TiTiler serving
- time-series indexing
PASS CRITERIA: two dates can be selected and rendered consistently.

### PHASE 4 — Change Detection AI
- baseline detector first.
- integrate Open-CD.
- dataset preparation.
- geographic train/val/test split.
- metrics dashboard.
- inference endpoint returns georeferenced mask/polygon.
PASS CRITERIA: actual test AOI returns reproducible change output and metrics.

### PHASE 5 — Forest Investigation
- before/after
- evidence chain
- fire/weather/soil/roads/protected-area context
- fragmentation
- carbon estimate
- news context
- source provenance
PASS CRITERIA: clicking hotspot produces complete investigation from real sources.

### PHASE 6 — Intelligence
- risk prediction
- SHAP explainability
- warning levels
- priority engine
- threat cascade
- forest resilience
- recovery
- what-if
PASS CRITERIA: predictions are explainable and clearly marked as estimates.

### PHASE 7 — Action
- GraphHopper/OSRM + OR-Tools routing.
- intervention suggestions.
- report generation.
- natural-language spatial query.
PASS CRITERIA: route/report/query operate on stored real data.

### PHASE 8 — Polish
- performance
- caching
- skeleton/loading states
- empty/error states
- source badges
- latency indicators
- demo seed AOIs using real cached data
- end-to-end tests

## Agent strategy
If running parallel agents:
- Agent A: frontend/map
- Agent B: satellite ingestion
- Agent C: environmental sources
- Agent D: AI
- Agent E: backend/database
- Agent F: QA
Each must work in isolated files/branches. Integrate only after tests.

## Deliverables
At each phase produce:
- code
- tests
- updated README
- API docs
- screenshots only after real UI works
- known limitations
- exact next tasks

## FINAL BEHAVIOR
When given this file, first:
1. inspect current repository state;
2. produce a concise implementation plan;
3. create Phase 0/1 only;
4. test it;
5. report what passed/failed;
6. wait for the next instruction rather than racing ahead into all 37 features.