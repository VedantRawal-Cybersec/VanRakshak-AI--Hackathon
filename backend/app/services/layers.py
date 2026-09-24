LAYER_GROUPS = [
    {"id":"satellite","label":"Satellite Imagery","icon":"🛰️","layers":[
        {"id":"sentinel2","label":"Sentinel-2 Optical","source":"Copernicus","freshness":"DYNAMIC_RECENT","resolution_m":10},
        {"id":"sentinel1","label":"Sentinel-1 Radar","source":"Copernicus/ASF","freshness":"DYNAMIC_RECENT","resolution_m":10},
        {"id":"landsat","label":"Landsat","source":"USGS/NASA","freshness":"DYNAMIC_RECENT","resolution_m":30},
        {"id":"true_color","label":"True Color","source":"Satellite derived","freshness":"DYNAMIC_RECENT"},
        {"id":"false_color","label":"False Color","source":"Satellite derived","freshness":"DYNAMIC_RECENT"},
    ]},
    {"id":"forest","label":"Forest","icon":"🌳","layers":[
        {"id":"forest_cover","label":"Forest Cover","source":"Dynamic World/GFW","freshness":"DYNAMIC_RECENT"},
        {"id":"forest_loss","label":"Forest Loss","source":"GFW/Hansen/VanRakshak","freshness":"DYNAMIC_RECENT"},
        {"id":"forest_gain","label":"Forest Gain","source":"Reference/derived","freshness":"HISTORICAL"},
        {"id":"biomass","label":"Biomass","source":"GEDI/derived","freshness":"REFERENCE"},
        {"id":"fragmentation","label":"Fragmentation","source":"VanRakshak derived","freshness":"AI_ESTIMATE"},
    ]},
    {"id":"vegetation","label":"Vegetation","icon":"🌿","layers":[
        {"id":"ndvi","label":"NDVI","source":"Sentinel/Landsat derived","freshness":"DYNAMIC_RECENT"},
        {"id":"ndmi","label":"NDMI / Moisture","source":"Sentinel/Landsat derived","freshness":"DYNAMIC_RECENT"},
        {"id":"nbr","label":"NBR / Burn","source":"Sentinel/Landsat derived","freshness":"DYNAMIC_RECENT"},
        {"id":"ndwi","label":"NDWI / Water","source":"Sentinel/Landsat derived","freshness":"DYNAMIC_RECENT"},
    ]},
    {"id":"fire","label":"Fire","icon":"🔥","layers":[
        {"id":"active_fire","label":"Active Fires","source":"NASA FIRMS","freshness":"LIVE_NRT"},
        {"id":"burned_area","label":"Burned Area","source":"NASA/derived","freshness":"DYNAMIC_RECENT"},
        {"id":"fire_risk","label":"Fire Risk","source":"VanRakshak","freshness":"AI_ESTIMATE"},
    ]},
    {"id":"climate","label":"Climate & Weather","icon":"🌡️","layers":[
        {"id":"temperature","label":"Temperature","source":"Open-Meteo","freshness":"FORECAST"},
        {"id":"rainfall","label":"Rainfall","source":"Open-Meteo","freshness":"FORECAST"},
        {"id":"humidity","label":"Humidity","source":"Open-Meteo","freshness":"FORECAST"},
        {"id":"wind","label":"Wind","source":"Open-Meteo","freshness":"FORECAST"},
        {"id":"cloud_cover","label":"Cloud Cover","source":"Open-Meteo","freshness":"FORECAST"},
    ]},
    {"id":"water","label":"Water & Drought","icon":"🌧️","layers":[
        {"id":"soil_moisture","label":"Soil Moisture","source":"Open-Meteo/model","freshness":"FORECAST"},
        {"id":"drought","label":"Drought / Water Stress","source":"VanRakshak derived","freshness":"AI_ESTIMATE"},
        {"id":"evapotranspiration","label":"Evapotranspiration","source":"Open-Meteo","freshness":"FORECAST"},
    ]},
    {"id":"soil","label":"Soil","icon":"🌱","layers":[
        {"id":"soil_ph","label":"Soil pH","source":"SoilGrids","freshness":"REFERENCE"},
        {"id":"soc","label":"Organic Carbon","source":"SoilGrids","freshness":"REFERENCE"},
        {"id":"nitrogen","label":"Nitrogen","source":"SoilGrids","freshness":"REFERENCE"},
        {"id":"texture","label":"Clay / Sand / Silt","source":"SoilGrids","freshness":"REFERENCE"},
    ]},
    {"id":"terrain","label":"Terrain","icon":"🏔️","layers":[
        {"id":"elevation","label":"Elevation / DEM","source":"SRTM/DEM","freshness":"REFERENCE"},
        {"id":"slope","label":"Slope","source":"DEM derived","freshness":"REFERENCE"},
        {"id":"erosion","label":"Erosion Susceptibility","source":"VanRakshak derived","freshness":"AI_ESTIMATE"},
    ]},
    {"id":"human","label":"Human Pressure","icon":"🚧","layers":[
        {"id":"roads","label":"Roads & Tracks","source":"OpenStreetMap","freshness":"DYNAMIC_RECENT"},
        {"id":"settlements","label":"Settlements","source":"OpenStreetMap","freshness":"DYNAMIC_RECENT"},
        {"id":"industrial","label":"Industry / Quarry / Mine","source":"OpenStreetMap","freshness":"DYNAMIC_RECENT"},
    ]},
    {"id":"conservation","label":"Conservation","icon":"🏞️","layers":[
        {"id":"protected","label":"Protected Areas","source":"Protected Planet/Bhuvan","freshness":"REFERENCE"},
    ]},
    {"id":"carbon","label":"Carbon / Biomass","icon":"🧮","layers":[
        {"id":"carbon_stock","label":"Estimated Carbon Stock","source":"GEDI/derived","freshness":"AI_ESTIMATE"},
        {"id":"carbon_loss","label":"Estimated Carbon Loss","source":"VanRakshak","freshness":"AI_ESTIMATE"},
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
