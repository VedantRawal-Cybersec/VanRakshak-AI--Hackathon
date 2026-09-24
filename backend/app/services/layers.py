LAYER_GROUPS = [
    {"id":"satellite","label":"Satellite Imagery","icon":"🛰️","layers":[
        {"id":"true_color","label":"Sentinel-2 True Color","source":"Earth Search / Sentinel-2","freshness":"DYNAMIC_RECENT","resolution_m":10,"render":"satellite","mode":"true_color"},
        {"id":"false_color","label":"Sentinel-2 False Color","source":"Earth Search / Sentinel-2","freshness":"DYNAMIC_RECENT","resolution_m":10,"render":"satellite","mode":"false_color"},
        {"id":"sentinel2","label":"Sentinel-2 Optical Catalogue","source":"Copernicus","freshness":"DYNAMIC_RECENT","resolution_m":10,"render":"metadata"},
        {"id":"sentinel1","label":"Sentinel-1 Radar","source":"Copernicus / ASF","freshness":"DYNAMIC_RECENT","resolution_m":10,"render":"planned_adapter"},
        {"id":"landsat","label":"Landsat","source":"USGS/NASA / Earth Search","freshness":"DYNAMIC_RECENT","resolution_m":30,"render":"metadata"},
    ]},
    {"id":"forest","label":"Forest","icon":"🌳","layers":[
        {"id":"forest_cover","label":"Forest / Tree Probability","source":"Dynamic World","freshness":"DYNAMIC_RECENT","resolution_m":10,"render":"earth_engine","ee_layer":"dynamic_world_trees"},
        {"id":"forest_loss","label":"Integrated Forest Disturbance Alerts","source":"Global Forest Watch","freshness":"DYNAMIC_RECENT","render":"gfw","dataset":"gfw_integrated_alerts"},
        {"id":"glad_s2","label":"GLAD Sentinel-2 Alerts","source":"Global Forest Watch","freshness":"DYNAMIC_RECENT","render":"gfw","dataset":"umd_glad_sentinel2_alerts"},
        {"id":"hansen_loss","label":"Historical Tree Cover Loss","source":"Hansen / Earth Engine","freshness":"HISTORICAL","resolution_m":30,"render":"earth_engine","ee_layer":"hansen_lossyear"},
        {"id":"tree_cover_2000","label":"Tree Cover Density 2000","source":"GFW","freshness":"REFERENCE","render":"gfw","dataset":"umd_tree_cover_density_2000"},
        {"id":"forest_gain","label":"Tree Cover Gain","source":"Global Forest Watch","freshness":"HISTORICAL","render":"gfw","dataset":"umd_tree_cover_gain"},
        {"id":"biomass","label":"GEDI Aboveground Biomass Density","source":"NASA GEDI / Earth Engine","freshness":"REFERENCE","resolution_m":25,"render":"earth_engine","ee_layer":"gedi_agbd"},
        {"id":"fragmentation","label":"Fragmentation","source":"VanRakshak raster analysis","freshness":"AI_ESTIMATE","render":"analysis"},
    ]},
    {"id":"vegetation","label":"Vegetation","icon":"🌿","layers":[
        {"id":"ndvi","label":"NDVI","source":"Sentinel-2 derived","freshness":"DYNAMIC_RECENT","resolution_m":10,"render":"satellite","mode":"ndvi"},
        {"id":"ndmi","label":"NDMI / Moisture","source":"Sentinel-2 derived","freshness":"DYNAMIC_RECENT","resolution_m":20,"render":"satellite","mode":"ndmi"},
        {"id":"nbr","label":"NBR / Burn","source":"Sentinel-2 derived","freshness":"DYNAMIC_RECENT","resolution_m":20,"render":"satellite","mode":"nbr"},
        {"id":"ndwi","label":"NDWI / Water","source":"Sentinel-2 derived","freshness":"DYNAMIC_RECENT","resolution_m":10,"render":"satellite","mode":"ndwi"},
        {"id":"vegetation_health","label":"Vegetation Health / Recovery","source":"VanRakshak time-series","freshness":"AI_ESTIMATE","render":"analysis"},
    ]},
    {"id":"fire","label":"Fire","icon":"🔥","layers":[
        {"id":"active_fire","label":"Active Fires","source":"NASA FIRMS NOAA-21","freshness":"LIVE_NRT","render":"firms_points"},
        {"id":"burned_area","label":"Burned Area","source":"MODIS / Earth Engine","freshness":"DYNAMIC_RECENT","resolution_m":500,"render":"earth_engine","ee_layer":"modis_burned_area"},
        {"id":"fire_loss","label":"Tree Cover Loss From Fires","source":"GFW","freshness":"HISTORICAL","render":"gfw","dataset":"umd_tree_cover_loss_from_fires"},
        {"id":"fire_risk","label":"Fire Risk","source":"VanRakshak","freshness":"AI_ESTIMATE","render":"analysis"},
    ]},
    {"id":"climate","label":"Climate & Weather","icon":"🌡️","layers":[
        {"id":"temperature","label":"Temperature","source":"Open-Meteo","freshness":"FORECAST","render":"point_data"},
        {"id":"surface_temperature","label":"Surface Temperature","source":"MODIS / Earth Engine","freshness":"DYNAMIC_RECENT","resolution_m":1000,"render":"earth_engine","ee_layer":"modis_lst"},
        {"id":"rainfall","label":"Rainfall","source":"Open-Meteo / CHIRPS","freshness":"FORECAST","render":"point_data"},
        {"id":"chirps","label":"Rainfall Raster","source":"CHIRPS / Earth Engine","freshness":"DYNAMIC_RECENT","resolution_m":5566,"render":"earth_engine","ee_layer":"chirps_rainfall"},
        {"id":"humidity","label":"Humidity","source":"Open-Meteo","freshness":"FORECAST","render":"point_data"},
        {"id":"wind","label":"Wind","source":"Open-Meteo","freshness":"FORECAST","render":"point_data"},
        {"id":"cloud_cover","label":"Cloud Cover","source":"Open-Meteo / Sentinel metadata","freshness":"FORECAST","render":"point_data"},
        {"id":"temperature_anomaly","label":"Temperature Anomaly","source":"VanRakshak baseline","freshness":"AI_ESTIMATE","render":"analysis"},
        {"id":"rainfall_anomaly","label":"Rainfall Anomaly","source":"VanRakshak baseline","freshness":"AI_ESTIMATE","render":"analysis"},
    ]},
    {"id":"water","label":"Water & Drought","icon":"🌧️","layers":[
        {"id":"soil_moisture","label":"Soil Moisture","source":"Open-Meteo model","freshness":"FORECAST","render":"point_data"},
        {"id":"drought","label":"Drought / Water Stress","source":"VanRakshak derived","freshness":"AI_ESTIMATE","render":"analysis"},
        {"id":"surface_water","label":"Surface Water Occurrence","source":"JRC / Earth Engine","freshness":"HISTORICAL","resolution_m":30,"render":"earth_engine","ee_layer":"jrc_water_occurrence"},
        {"id":"evapotranspiration","label":"Evapotranspiration","source":"Open-Meteo","freshness":"FORECAST","render":"point_data"},
        {"id":"precipitation","label":"Precipitation","source":"Open-Meteo / CHIRPS","freshness":"DYNAMIC_RECENT","render":"point_data"},
    ]},
    {"id":"soil","label":"Soil","icon":"🌱","layers":[
        {"id":"soil_type","label":"Soil Profile","source":"SoilGrids","freshness":"REFERENCE","resolution_m":250,"render":"point_data"},
        {"id":"soil_ph","label":"Soil pH","source":"SoilGrids","freshness":"REFERENCE","resolution_m":250,"render":"point_data"},
        {"id":"soc","label":"Organic Carbon","source":"SoilGrids","freshness":"REFERENCE","resolution_m":250,"render":"point_data"},
        {"id":"nitrogen","label":"Nitrogen","source":"SoilGrids","freshness":"REFERENCE","resolution_m":250,"render":"point_data"},
        {"id":"texture","label":"Clay / Sand / Silt","source":"SoilGrids","freshness":"REFERENCE","resolution_m":250,"render":"point_data"},
        {"id":"bulk_density","label":"Bulk Density","source":"SoilGrids","freshness":"REFERENCE","resolution_m":250,"render":"point_data"},
        {"id":"cec","label":"CEC / Fertility Proxy","source":"SoilGrids","freshness":"REFERENCE","resolution_m":250,"render":"point_data"},
    ]},
    {"id":"terrain","label":"Terrain","icon":"🏔️","layers":[
        {"id":"elevation","label":"Elevation / DEM","source":"SRTM / Earth Engine","freshness":"REFERENCE","resolution_m":30,"render":"earth_engine","ee_layer":"srtm_elevation"},
        {"id":"slope","label":"Slope","source":"SRTM / Earth Engine","freshness":"REFERENCE","resolution_m":30,"render":"earth_engine","ee_layer":"srtm_slope"},
        {"id":"aspect","label":"Aspect","source":"SRTM / Earth Engine","freshness":"REFERENCE","resolution_m":30,"render":"earth_engine","ee_layer":"srtm_aspect"},
        {"id":"erosion","label":"Erosion Susceptibility","source":"VanRakshak derived","freshness":"AI_ESTIMATE","render":"analysis"},
    ]},
    {"id":"landcover","label":"Land Cover","icon":"🌍","layers":[
        {"id":"dynamic_world","label":"Dynamic World Land Cover","source":"Google Earth Engine","freshness":"DYNAMIC_RECENT","resolution_m":10,"render":"earth_engine","ee_layer":"dynamic_world_label"},
    ]},
    {"id":"human","label":"Human Pressure","icon":"🚧","layers":[
        {"id":"roads","label":"Roads & Tracks","source":"OpenStreetMap","freshness":"DYNAMIC_RECENT","render":"overpass"},
        {"id":"settlements","label":"Settlements","source":"OpenStreetMap","freshness":"DYNAMIC_RECENT","render":"overpass"},
        {"id":"industrial","label":"Industry / Quarry / Mine","source":"OpenStreetMap","freshness":"DYNAMIC_RECENT","render":"overpass"},
        {"id":"population","label":"Population","source":"WorldPop / Earth Engine","freshness":"REFERENCE","resolution_m":100,"render":"earth_engine","ee_layer":"worldpop_population"},
        {"id":"human_modification","label":"Human Modification","source":"CSP / Earth Engine","freshness":"REFERENCE","resolution_m":1000,"render":"earth_engine","ee_layer":"human_modification"},
    ]},
    {"id":"conservation","label":"Conservation","icon":"🏞️","layers":[
        {"id":"protected","label":"Protected Areas","source":"UNEP-WCMC WDPA / Earth Engine","freshness":"REFERENCE","render":"earth_engine","ee_layer":"wdpa_protected"},
    ]},
    {"id":"carbon","label":"Carbon / Biomass","icon":"🧮","layers":[
        {"id":"carbon_stock","label":"Carbon Density (reference)","source":"UNEP-WCMC / Earth Engine","freshness":"REFERENCE","resolution_m":300,"render":"earth_engine","ee_layer":"wcmc_carbon_density"},
        {"id":"carbon_loss","label":"Estimated Carbon Loss","source":"VanRakshak","freshness":"AI_ESTIMATE","render":"analysis"},
    ]},
]

FEATURES = [
"Real Satellite Monitoring","Forest Cover Monitoring","AI Deforestation Detection","Before–After Satellite Comparison",
"Multi-Spectral Analysis","Multi-Layer Earth Map","Deep Region Investigation","Temperature Intelligence","Weather Intelligence",
"Drought & Water Stress","Fire & Heat Detection","Vegetation Health","Environmental Anomaly Radar","AI Forest Doctor",
"Smart Warning System","Threat Prediction","Threat Cascade Engine","AI Priority Engine","Investigation/Patrol Optimizer",
"AI What-If Simulator","Intervention Engine","Recovery Intelligence","Recovery Exit Conditions","Forest Resilience Score",
"Protected Area Intelligence","Forest Fragmentation Analysis","Carbon Loss Calculator","Climate–Forest Correlation",
"AI Evidence Chain","Explainable AI","Natural-Language Earth Query","Automatic Investigation Report","Regional Threat Comparison",
"Forest Time Machine","Live Command Center","Forest Digital Profile","News & Internet Intelligence"
]
