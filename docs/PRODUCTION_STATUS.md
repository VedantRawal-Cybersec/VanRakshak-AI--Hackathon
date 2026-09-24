# VanRakshak AI — Production / Hackathon Status

This document is deliberately strict. A feature is only described as working when there is an executable code path. External services that require credentials remain credential-gated; the application must never replace an unavailable provider with fabricated environmental values.

## Working without private provider credentials

- India-first MapLibre command center and interactive deep-region investigation.
- Sentinel-2 L2A catalogue search through public STAC endpoints.
- Real Sentinel-2 COG-backed true-color / false-color / NDVI / NDMI / NBR / NDWI map tiles through TiTiler.
- Before/after Sentinel scene comparison and synchronized split view.
- Remote multispectral change screening using cloud/shadow/snow masking and co-registered Sentinel bands.
- Candidate vegetation-loss polygons, area, spectral deltas, screening confidence and fragmentation changes.
- IsolationForest corroboration of unusual multispectral change. This is anomaly corroboration, not a trained deforestation classifier.
- Sentinel-1 scene-availability search through ASF for radar follow-up.
- Open-Meteo current weather plus same-season historical/reanalysis anomaly calculations.
- SoilGrids point properties.
- OpenStreetMap/Overpass human-pressure context.
- Nominatim India geocoding / reverse geocoding and search-boundary rendering.
- Global Forest Watch public raster layers where their public tile endpoint is available.
- GDELT contextual news search.
- Explainable evidence-normalized warning score, Forest Doctor, threat cascade, resilience, recovery, intervention, regional comparison and what-if tools.
- Forest Time Machine using real Sentinel-2 observations.
- Source-backed trend forecast baseline with uncertainty.
- Fragmentation metrics from raster masks.
- OSRM road route plus priority-aware patrol ordering.
- Automatic investigation PDF reports.
- SQLAlchemy persistence models and PostGIS/Redis/TiTiler/Celery Docker services.
- Feature capability registry covering exactly all 37 required features.

## Credential-gated integrations

### NASA FIRMS
Set `FIRMS_MAP_KEY`. Without it, the API reports the source as unavailable and does not invent a fire count.

### Protected Planet
Set `PROTECTED_PLANET_TOKEN` to use its API. Protected-area intelligence can alternatively use the Earth Engine WDPA layer when Earth Engine is configured.

### Google Earth Engine
Set `GOOGLE_CLOUD_PROJECT` and provide Application Default Credentials. Earth Engine enables Dynamic World, Hansen forest change, SRTM terrain, JRC water, MODIS LST/burned area, CHIRPS rainfall, GEDI biomass, WorldPop, human modification, WCMC carbon density and WDPA protected-area layers.

### MOSDAC
VanRakshak generates a validated configuration compatible with the official MOSDAC download client. Actual product download requires the user's MOSDAC account and a chosen official `datasetId`; credentials are never stored in this repository.

### ISRO Bhuvan
VanRakshak exposes an official WMS proxy. The user selects an exact Bhuvan-published layer name because layer availability is dataset-specific.

## Deep-learning model gate

The working default detector is a real-data multispectral change screen. The optional Open-CD production path is intentionally not marked as a trained model until a real checkpoint exists.

To promote an Open-CD model:

1. Build geographically separated train/validation/test areas.
2. Compare suitable Open-CD candidates such as TinyCD, Changer or ChangeFormer.
3. Measure Precision, Recall, F1, IoU/Dice, false-positive rate and inference latency.
4. Save the selected checkpoint and config.
5. Configure `OPENCD_REPO`, `OPENCD_CONFIG` and `OPENCD_CHECKPOINT`.
6. Record the actual experiment results. Never publish invented accuracy.

## Scientific / evidence limitations

- A candidate vegetation-loss polygon is a screening result, not legal proof of deforestation.
- News is supporting context only and never establishes cause or illegality.
- Nearby roads, settlements, mines or quarries are context/risk factors, not proof of a driver.
- Sentinel-1 scene availability is not radar confirmation; a measured SAR change is required for confirmation.
- SoilGrids is a modeled reference surface, not a field soil test.
- OSM mapping completeness varies, particularly on forest tracks.
- Carbon values are estimates and must retain the source density and uncertainty statement.
- Threat prediction and what-if outputs are risk/scenario estimates, not guaranteed forecasts.
- Satellite imagery is not continuous live video. The UI retains scene observation timestamps and source freshness.

## Deployment acceptance checks

Before a hackathon demo or production-like deployment:

1. `PYTHONPATH=backend pytest -q backend/tests` is green.
2. `python -m compileall backend/app` is green.
3. `node --check web/app.js` is green.
4. `/api/health` returns operational.
5. `/api/source-health` identifies unavailable providers instead of fabricating data.
6. TiTiler is reachable from the API and browser.
7. At least one chosen demo forest has two usable Sentinel observations.
8. Before/after multispectral screening returns real scene IDs and timestamps.
9. FIRMS key is configured if fire evidence is part of the demo.
10. Earth Engine credentials are configured if Dynamic World / Hansen / GEDI / WDPA / terrain layers are part of the demo.
