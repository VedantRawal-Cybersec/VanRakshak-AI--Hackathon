# Data Sources and Repositories

## Satellite / catalogues
- Copernicus Data Space STAC: https://documentation.dataspace.copernicus.eu/APIs/STAC.html
- EODAG: https://github.com/CS-SI/eodag
- PySTAC Client: https://github.com/stac-utils/pystac-client
- ODC-STAC: https://github.com/opendatacube/odc-stac
- Sentinel Hub Python: https://github.com/sentinel-hub/sentinelhub-py
- ASF Search: https://github.com/asfadmin/Discovery-asf_search
- ISRO MOSDAC: https://mosdac.gov.in/
- NASA GIBS: https://nasa-gibs.github.io/gibs-api-docs/
- NASA Worldview: https://github.com/nasa-gibs/worldview

## Forest / validation
- Dynamic World: https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1
- Hansen Global Forest Change: https://developers.google.com/earth-engine/datasets/catalog/UMD_hansen_global_forest_change_2025_v1_13
- Global Forest Watch: https://www.globalforestwatch.org/
- GFW code: https://github.com/wri/gfw
- GFW API examples: https://github.com/wri/data-api-examples
- GFW tiles: https://tiles.globalforestwatch.org/

## AI / geospatial ML
- Open-CD: https://github.com/likyoo/open-cd
- RSChange: https://github.com/xwmaxwma/rschange
- TorchGeo: https://github.com/microsoft/torchgeo
- TerraTorch: https://github.com/IBM/terratorch
- NASA Prithvi EO 2.0: https://github.com/NASA-IMPACT/Prithvi-EO-2.0
- Clay: https://github.com/Clay-foundation/model
- SamGeo: https://github.com/opengeos/segment-geospatial

## Environmental
- NASA FIRMS: https://firms.modaps.eosdis.nasa.gov/
- Open-Meteo: https://open-meteo.com/
- SoilGrids: https://soilgrids.org/
- Protected Planet API v4: https://api.protectedplanet.net/documentation
- OpenStreetMap / Overpass: https://wiki.openstreetmap.org/wiki/Overpass_API
- GDELT DOC: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- NASA GEDI: https://gedi.umd.edu/
- ISRO Bhuvan: https://bhuvan.nrsc.gov.in/

## Geospatial / serving
- Rasterio: https://github.com/rasterio/rasterio
- GeoPandas: https://github.com/geopandas/geopandas
- xarray: https://github.com/pydata/xarray
- TiTiler: https://github.com/developmentseed/titiler
- rio-tiler: https://github.com/cogeotiff/rio-tiler
- PostGIS: https://github.com/postgis/postgis
- PgSTAC: https://github.com/stac-utils/pgstac

## Dashboard / routing
- MapLibre GL JS: https://github.com/maplibre/maplibre-gl-js
- deck.gl: https://github.com/visgl/deck.gl
- Apache ECharts: https://github.com/apache/echarts
- GraphHopper: https://github.com/graphhopper/graphhopper
- OR-Tools: https://github.com/google/or-tools

## Model / experiment operations
- XGBoost: https://github.com/dmlc/xgboost
- SHAP: https://github.com/shap/shap
- MLflow: https://github.com/mlflow/mlflow
- DVC: https://github.com/iterative/dvc
- CVAT: https://github.com/cvat-ai/cvat

## Current operational notes
- NASA FIRMS Area API requires a free MAP key.
- Protected Planet API v4 requires a token.
- SoilGrids REST is beta/fair-use and can have downtime; cache requests.
- Copernicus STAC is used for catalogue discovery. Pixel access/processing should use an approved data-access path rather than assuming every STAC asset is anonymously downloadable.
