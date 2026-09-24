# VanRakshak AI — Data Sources, APIs and Repositories

This file is intentionally explicit. VanRakshak separates **runtime providers** from **research/reference repositories**. A repository appearing here does not mean it is blindly vendored into the project.

## 1. Satellite discovery / Earth observation

- Copernicus Data Space STAC — https://documentation.dataspace.copernicus.eu/APIs/STAC.html
- Copernicus Browser — https://github.com/eu-cdse/copernicus-browser
- Element 84 Earth Search — https://github.com/Element84/earth-search
- EODAG — https://github.com/CS-SI/eodag
- PySTAC Client — https://github.com/stac-utils/pystac-client
- ODC-STAC — https://github.com/opendatacube/odc-stac
- stackstac — https://github.com/gjoseph92/stackstac
- Sentinel Hub Python — https://github.com/sentinel-hub/sentinelhub-py
- ASF Search / Sentinel-1 — https://github.com/asfadmin/Discovery-asf_search
- NASA GIBS API — https://nasa-gibs.github.io/gibs-api-docs/
- NASA Worldview — https://github.com/nasa-gibs/worldview
- NASA GIBS examples — https://github.com/nasa-gibs/gibs-web-examples
- Google Earth Engine API client — https://github.com/google/earthengine-api

### Runtime use in VanRakshak

- Copernicus STAC: authoritative Sentinel-2 catalogue metadata.
- Earth Search: public Sentinel-2 L2A STAC/COG path used for visual tile rendering and multispectral analysis.
- ASF: Sentinel-1 radar-scene discovery.
- Google Earth Engine Python API: authenticated access to Dynamic World, Hansen, GEDI, SRTM, MODIS, CHIRPS, WDPA and other catalog layers.

## 2. Forest / land-cover / disturbance

- Dynamic World V1 — https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1
- Hansen Global Forest Change 2025 v1.13 — https://developers.google.com/earth-engine/datasets/catalog/UMD_hansen_global_forest_change_2025_v1_13
- Global Forest Watch — https://www.globalforestwatch.org/
- GFW GitHub — https://github.com/wri/gfw
- GFW Data API — https://github.com/wri/gfw-data-api
- GFW API examples — https://github.com/wri/data-api-examples
- GFW raster tiles — https://tiles.globalforestwatch.org/
- Forest Watcher — https://github.com/forest-watcher/forest-watcher

VanRakshak supports GFW Integrated Alerts raster tiles and Earth Engine-backed Dynamic World/Hansen layers.

## 3. AI change detection / geospatial ML

- Open-CD — https://github.com/likyoo/open-cd
- RSChange — https://github.com/xwmaxwma/rschange
- TorchGeo — https://github.com/torchgeo/torchgeo
- TerraTorch — https://github.com/torchgeo/terratorch
- NASA Prithvi EO 2.0 — https://github.com/NASA-IMPACT/Prithvi-EO-2.0
- Clay — https://github.com/Clay-foundation/model
- SamGeo / Segment-Geospatial — https://github.com/opengeos/segment-geospatial
- XGBoost — https://github.com/dmlc/xgboost
- SHAP — https://github.com/shap/shap
- scikit-learn — https://github.com/scikit-learn/scikit-learn

VanRakshak ships a working source-backed multispectral change baseline and an explicit Open-CD runtime handoff. A deep model is not labelled validated until a real checkpoint and evaluation metrics exist.

## 4. Raster / vector processing

- s2cloudless — https://github.com/sentinel-hub/sentinel2-cloud-detector
- eo-learn — https://github.com/sentinel-hub/eo-learn
- Rasterio — https://github.com/rasterio/rasterio
- GeoPandas — https://github.com/geopandas/geopandas
- xarray — https://github.com/pydata/xarray
- rio-cogeo — https://github.com/cogeotiff/rio-cogeo
- rio-tiler — https://github.com/cogeotiff/rio-tiler
- TiTiler — https://github.com/developmentseed/titiler
- Sentinel Hub custom scripts — https://github.com/sentinel-hub/custom-scripts
- geemap — https://github.com/gee-community/geemap
- leafmap — https://github.com/opengeos/leafmap

## 5. Fire / heat

- NASA FIRMS — https://firms.modaps.eosdis.nasa.gov/
- FIRMS API — https://firms.modaps.eosdis.nasa.gov/api/
- FIRMS WMS — https://firms.modaps.eosdis.nasa.gov/mapserver/wms-info/

Runtime note: FIRMS Area API requires a free MAP key.

## 6. Climate / weather / drought

- Open-Meteo — https://open-meteo.com/
- Historical API — https://open-meteo.com/en/docs/historical-weather-api
- ECMWF API — https://open-meteo.com/en/docs/ecmwf-api
- CHIRPS via Earth Engine — https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY

## 7. Soil

- SoilGrids — https://soilgrids.org/
- SoilGrids documentation — https://docs.isric.org/globaldata/soilgrids/

SoilGrids fields are modelled reference estimates, not field measurements.

## 8. India-specific geospatial sources

- ISRO Bhuvan — https://bhuvan.nrsc.gov.in/
- Bhuvan services — https://bhuvan.nrsc.gov.in/bhuvan_links.php
- NRSC — https://www.nrsc.gov.in/
- MOSDAC — https://mosdac.gov.in/
- MOSDAC Download API manual — https://mosdac.gov.in/downloadapi-manual

VanRakshak contains a Bhuvan WMS proxy and MOSDAC official-client configuration helper. MOSDAC authenticated downloads must use user-owned credentials outside Git.

## 9. Protected areas / conservation

- Protected Planet — https://www.protectedplanet.net/
- Protected Planet API v4 — https://api.protectedplanet.net/documentation
- WDPA Earth Engine polygons — https://developers.google.com/earth-engine/datasets/catalog/WCMC_WDPA_current_polygons

## 10. Roads / settlements / human pressure

- OpenStreetMap — https://www.openstreetmap.org/
- Overpass API — https://wiki.openstreetmap.org/wiki/Overpass_API
- Overpass Turbo — https://overpass-turbo.eu/
- Global Human Modification via Earth Engine — https://developers.google.com/earth-engine/datasets/
- WorldPop via Earth Engine — https://developers.google.com/earth-engine/datasets/

OSM completeness varies. Missing mapped features never prove absence on the ground.

## 11. News/context

- GDELT — https://www.gdeltproject.org/
- GDELT DOC API — https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

News is supporting context only. VanRakshak does not use article correlation as proof of a deforestation driver.

## 12. Carbon / biomass

- NASA GEDI — https://gedi.umd.edu/
- NASA Earthdata Search — https://search.earthdata.nasa.gov/
- GEDI L4A monthly raster — https://developers.google.com/earth-engine/datasets/catalog/LARSE_GEDI_GEDI04_A_002_MONTHLY
- ORNL DAAC GEDI — https://daac.ornl.gov/GEDI/

## 13. Fragmentation / network modelling

- PyLandStats — https://github.com/martibosch/pylandstats
- NetworkX — https://github.com/networkx/networkx

VanRakshak also implements lightweight raster fragmentation metrics internally so the core demo does not require PyLandStats at runtime.

## 14. Patrol routing

- OSRM — https://github.com/Project-OSRM/osrm-backend
- GraphHopper — https://github.com/graphhopper/graphhopper
- Google OR-Tools — https://github.com/google/or-tools

Current runtime path uses priority-aware ordering plus OSRM road geometry, with graceful straight-line fallback.

## 15. Frontend / dashboard

- MapLibre GL JS — https://github.com/maplibre/maplibre-gl-js
- deck.gl — https://github.com/visgl/deck.gl
- Apache ECharts — https://github.com/apache/echarts

The current hackathon UI deliberately keeps dependencies light and map-first; these libraries are reference options for higher-volume overlays and advanced analytics.

## 16. Storage / jobs / serving

- PostgreSQL — https://www.postgresql.org/
- PostGIS — https://github.com/postgis/postgis
- PgSTAC — https://github.com/stac-utils/pgstac
- Redis — https://github.com/redis/redis
- Celery — https://github.com/celery/celery
- FastAPI — https://github.com/fastapi/fastapi

## 17. Reporting / annotation / ML operations

- WeasyPrint — https://github.com/Kozea/WeasyPrint
- ReportLab — https://github.com/MrBitBucket/reportlab-mirror
- CVAT — https://github.com/cvat-ai/cvat
- MLflow — https://github.com/mlflow/mlflow
- DVC — https://github.com/iterative/dvc

## Data-integrity requirements

1. Always show source and freshness when a value is source-backed.
2. Do not call delayed satellite imagery continuous live video.
3. Do not fabricate values when a source is down or unconfigured.
4. Do not call a correlation a cause.
5. Do not call an AI risk estimate a confirmed event.
6. Do not call a nearby road/mining feature proof of illegal activity.
7. Keep API credentials out of source control.
