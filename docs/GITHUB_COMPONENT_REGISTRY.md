# VanRakshak AI — GitHub Component Registry

This registry is the curated implementation map for completing VanRakshak AI. It intentionally favors official, maintained, production-grade repositories and keeps the uploaded VanRakshak dashboard reference as the visual source of truth.

## Dashboard rule

Do **not** copy another dashboard wholesale. Rebuild the VanRakshak UI to match the approved uploaded reference: dark command-center theme, compact left navigation, India-first map occupying most of the screen, right investigation panel, KPI strip, before/after imagery, evidence/risk cards, bottom trends/alerts, layer controls, source/freshness badges and one-click investigation/report actions.

Borrow behavior/components from the repositories below, not their brand identity.

## 1. Forest monitoring / deforestation intelligence

- https://github.com/wri/gfw — Global Forest Watch web app. Use for forest-monitoring UX patterns, alert/layer organization and investigation flows.
- https://github.com/forest-watcher/forest-watcher — GFW field response workflows, alert review, reports, routes and offline concepts.
- https://github.com/forestdatapartnership/whisp — convergence-of-evidence forest risk engine and multi-dataset forest/disturbance logic.
- https://github.com/forestdatapartnership/whisp-app — excellent architectural reference: Next.js + FastAPI + Celery + Redis + PostgreSQL + Earth Engine workers.
- https://github.com/google/forest-data-partnership — public forest-risk models/artifacts and Earth Engine model-hosting examples.
- https://github.com/terrabrasilis/deforestation_dashboard — deforestation analytics/dashboard patterns.
- https://github.com/rhammell/forest-watch — historical satellite imagery, true/false color and NDVI forest monitoring UI.
- https://github.com/openforis/sepal — large-scale forest/land monitoring platform reference.
- https://github.com/openforis/collect-earth — forest inventory/validation and visual interpretation workflow reference.

## 2. AI / remote-sensing change detection

- https://github.com/likyoo/open-cd — primary deep change-detection toolbox. Supports Changer, ChangeFormer, TinyCD and multiple datasets.
- https://github.com/xwmaxwma/rschange — additional remote-sensing change-detection research/tooling.
- https://github.com/circleLZY/JL1-CD — current change-detection benchmark/dataset built on Open-CD.
- https://github.com/NASA-IMPACT/Prithvi-EO-2.0 — NASA/IBM multi-temporal Earth-observation foundation model.
- https://github.com/torchgeo/terratorch — fine-tuning framework for Prithvi, Clay and other geospatial foundation models.
- https://github.com/torchgeo/torchgeo — geospatial datasets/samplers/models for PyTorch.
- https://github.com/Clay-foundation/model — Clay geospatial foundation model.
- https://github.com/opengeos/segment-geospatial — SamGeo/SAM-based geospatial segmentation and REST serving.

Recommended VanRakshak path:
1. Keep the current transparent multispectral Sentinel baseline.
2. Train/validate Open-CD candidates on forest-change data.
3. Add Prithvi/TerraTorch only as a second-stage experiment if time/GPU permits.
4. Never publish model accuracy without geographic holdout validation.

## 3. Satellite discovery / STAC / imagery

- https://github.com/CS-SI/eodag — multi-provider Earth-observation search/download.
- https://github.com/stac-utils/pystac-client — STAC API client.
- https://github.com/opendatacube/odc-stac — load STAC items into analysis-ready xarray.
- https://github.com/gjoseph92/stackstac — STAC-to-xarray/Dask.
- https://github.com/Element84/earth-search — public cloud-native STAC catalogue reference.
- https://github.com/asfadmin/Discovery-asf_search — Sentinel-1 discovery/download client.
- https://github.com/sentinel-hub/sentinelhub-py — Sentinel Hub Python tooling.
- https://github.com/sentinel-hub/sentinel2-cloud-detector — s2cloudless cloud masking.
- https://github.com/sentinel-hub/eo-learn — EO processing workflows.
- https://github.com/eu-cdse/copernicus-browser — Copernicus Browser UI/interaction reference.
- https://github.com/google/earthengine-api — official Earth Engine client.

## 4. NASA fire / imagery / hazards

- https://github.com/nasa-gibs/gibs-web-examples — **must use** for direct MapLibre GIBS integration examples.
- https://github.com/nasa-gibs/worldview — **must study** for time slider, imagery layers, date navigation and satellite UX.
- https://github.com/nasa/api-docs — NASA public API catalogue/reference.
- https://github.com/api-evangelist/nasa-firms — reference-only OpenAPI/Postman descriptions; official FIRMS documentation remains source of truth.
- https://github.com/Francesco-Vitale/event-intelligence-dashboard — useful FastAPI + React + MapLibre FIRMS architecture reference.
- https://github.com/mdaninas/global-wildfire-risk-dashboard — fire-risk analytics reference.
- https://github.com/andresnaviaro-arch/fire-map — secure GitHub Actions FIRMS-key pattern.

Use official NASA FIRMS + GIBS endpoints in production. Add EONET directly from NASA's current v3 API.

## 5. Protected areas / conservation

- https://github.com/unepwcmc/protectedplanet-api — official Protected Planet API implementation; use v4.
- https://github.com/unepwcmc/ProtectedPlanet — protected-area platform architecture and UX reference.
- https://github.com/unepwcmc/protectedplanet-db — schema reference.

VanRakshak should implement protected-area search, parcels, site lookup, exact AOI intersection, IUCN category, governance, designation and Green List metadata.

## 6. Raster/vector processing and map tiles

- https://github.com/developmentseed/titiler — dynamic STAC/COG raster tiles. Use current modular TiTiler packages.
- https://github.com/cogeotiff/rio-tiler — raster tile reading.
- https://github.com/cogeotiff/rio-cogeo — COG creation/validation.
- https://github.com/rasterio/rasterio — raster IO.
- https://github.com/geopandas/geopandas — vector processing.
- https://github.com/pydata/xarray — multidimensional arrays/time series.
- https://github.com/stac-utils/pgstac — scalable STAC metadata in PostgreSQL.
- https://github.com/stac-utils/stac-fastapi — STAC API implementation.
- https://github.com/stac-utils/stac-fastapi-pgstac — FastAPI + PgSTAC production path.

## 7. Dashboard / geospatial frontend

- https://github.com/maplibre/maplibre-gl-js — base map renderer.
- https://github.com/visgl/deck.gl — high-volume overlays, arcs, heatmaps, polygons and GPU rendering.
- https://github.com/keplergl/kepler.gl — MapLibre/deck.gl large-data layer/filter UX reference.
- https://github.com/apache/echarts — command-center charts and trends.
- https://github.com/opengeos/vite-maplibre-react — clean React/TypeScript MapLibre starter.
- https://github.com/MChorfa/geolibre — React + TypeScript + MapLibre + deck.gl GIS workspace reference.
- https://github.com/opengeos/maplibre-gl-vector — dynamic vector dataset rendering.

The uploaded VanRakshak design remains the UI specification. These repositories supply rendering/interaction primitives only.

## 8. Weather / drought / soil / human pressure

- https://github.com/open-meteo/open-meteo — current weather, historical climate, flood and related APIs.
- SoilGrids API: use the official ISRIC REST endpoint directly. Third-party wrappers are optional only.
- OpenStreetMap / Overpass: use the official API for roads, settlements and mapped human pressure.
- https://github.com/Project-OSRM/osrm-backend — road routing.

## 9. Fragmentation / risk / explainability / graph logic

- https://github.com/martibosch/pylandstats — landscape/fragmentation metrics.
- https://github.com/dmlc/xgboost — tabular threat/risk model.
- https://github.com/shap/shap — model explanations.
- https://github.com/networkx/networkx — threat cascade / graph relationships.
- https://github.com/google/or-tools — multi-stop patrol optimization.
- https://github.com/graphhopper/graphhopper — routing alternative if a dedicated routing backend is deployed.

## 10. Workers / storage / observability / MLOps

- https://github.com/postgis/postgis — spatial persistence.
- https://github.com/celery/celery — asynchronous satellite/AI jobs.
- https://github.com/redis/redis — queue/cache.
- https://github.com/mlflow/mlflow — model experiment tracking.
- https://github.com/iterative/dvc — dataset/model versioning.
- https://github.com/cvat-ai/cvat — change-mask/manual annotation and QA.
- https://github.com/prometheus/prometheus — service metrics.
- https://github.com/grafana/grafana — operational monitoring.

## Final recommended implementation stack

**Frontend:** Next.js + TypeScript + MapLibre + deck.gl + ECharts.

**Backend:** FastAPI + PostgreSQL/PostGIS + PgSTAC + Redis + Celery + TiTiler.

**Satellite:** Copernicus/Earth Search Sentinel-2 + ASF Sentinel-1 + Earth Engine + NASA GIBS.

**Forest evidence:** GFW + Whisp-style convergence of evidence + Dynamic World + Hansen + GLAD/DIST/RADD-compatible datasets where available.

**Fire:** NASA FIRMS NOAA-21 NRT primary, NOAA-20 NRT and MODIS NRT corroboration, plus GIBS thermal imagery and EONET hazard context.

**AI:** multispectral baseline + validated Open-CD model; optional Prithvi/TerraTorch experiments.

**Conservation:** Protected Planet v4 + Earth Engine WDPA/WCMC layers.

**Context:** Open-Meteo, SoilGrids, OSM/Overpass, GEDI, Bhuvan/MOSDAC, GDELT.

## What not to do

- Do not vendor entire external repositories into VanRakshak.
- Do not copy visual branding or copyrighted assets.
- Do not make third-party mirrors the source of truth when an official provider exists.
- Do not hard-code API keys.
- Do not claim a trained AI model until a real checkpoint and evaluation exist.
- Do not call Sentinel imagery continuous live video.
