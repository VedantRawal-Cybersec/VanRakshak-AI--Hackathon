from __future__ import annotations
from datetime import datetime, timedelta, timezone
from app.adapters.base import AdapterError
from app.config import settings

EE_LAYERS = {
    "dynamic_world_trees": {"dataset": "GOOGLE/DYNAMICWORLD/V1", "kind": "collection", "band": "trees", "vis": {"min": 0, "max": 1, "palette": ["0b1f15", "1fd17f"]}, "freshness": "DYNAMIC_RECENT", "resolution_m": 10},
    "dynamic_world_label": {"dataset": "GOOGLE/DYNAMICWORLD/V1", "kind": "collection", "band": "label", "vis": {"min": 0, "max": 8, "palette": ["419bdf","397d49","88b053","7a87c6","e49635","dfc35a","c4281b","a59b8f","b39fe1"]}, "freshness": "DYNAMIC_RECENT", "resolution_m": 10},
    "hansen_lossyear": {"dataset": "UMD/hansen/global_forest_change_2025_v1_13", "kind": "image", "band": "lossyear", "vis": {"min": 1, "max": 25, "palette": ["ffff00","ff0000"]}, "freshness": "HISTORICAL", "resolution_m": 30},
    "hansen_treecover": {"dataset": "UMD/hansen/global_forest_change_2025_v1_13", "kind": "image", "band": "treecover2000", "vis": {"min": 0, "max": 100, "palette": ["f2efe9","006400"]}, "freshness": "REFERENCE", "resolution_m": 30},
    "srtm_elevation": {"dataset": "USGS/SRTMGL1_003", "kind": "image", "band": "elevation", "vis": {"min": 0, "max": 3500, "palette": ["0b3d2e","d9c98b","ffffff"]}, "freshness": "REFERENCE", "resolution_m": 30},
    "jrc_water_occurrence": {"dataset": "JRC/GSW1_4/GlobalSurfaceWater", "kind": "image", "band": "occurrence", "vis": {"min": 0, "max": 100, "palette": ["ffffff","0050ff"]}, "freshness": "HISTORICAL", "resolution_m": 30},
    "modis_lst": {"dataset": "MODIS/061/MOD11A1", "kind": "collection", "band": "LST_Day_1km", "vis": {"min": 13000, "max": 16500, "palette": ["313695","74add1","ffffbf","f46d43","a50026"]}, "freshness": "DYNAMIC_RECENT", "resolution_m": 1000},
    "chirps_rainfall": {"dataset": "UCSB-CHG/CHIRPS/DAILY", "kind": "collection", "band": "precipitation", "vis": {"min": 0, "max": 100, "palette": ["ffffff","a6cee3","1f78b4","08306b"]}, "freshness": "DYNAMIC_RECENT", "resolution_m": 5566},
    "modis_burned_area": {"dataset": "MODIS/061/MCD64A1", "kind": "collection", "band": "BurnDate", "vis": {"min": 1, "max": 366, "palette": ["ffffcc","fd8d3c","bd0026"]}, "freshness": "DYNAMIC_RECENT", "resolution_m": 500},
    "gedi_agbd": {"dataset": "LARSE/GEDI/GEDI04_A_002_MONTHLY", "kind": "collection", "band": "agbd", "vis": {"min": 0, "max": 300, "palette": ["fff7bc","7fcdbb","2c7fb8","253494"]}, "freshness": "REFERENCE", "resolution_m": 25, "quality": "gedi_l4a"},
    "worldpop_population": {"dataset": "WorldPop/GP/100m/pop", "kind": "collection", "band": "population", "vis": {"min": 0, "max": 50, "palette": ["24126c","1fff4f","d4ff50"]}, "freshness": "REFERENCE", "resolution_m": 100, "static_latest": True},
    "human_modification": {"dataset": "CSP/HM/GlobalHumanModification", "kind": "collection", "band": "gHM", "vis": {"min": 0, "max": 1, "palette": ["0c0c0c","071aff","ff0000","ffbd03","fffdfd"]}, "freshness": "REFERENCE", "resolution_m": 1000, "static_latest": True},
    "srtm_slope": {"dataset": "USGS/SRTMGL1_003", "kind": "terrain", "band": "slope", "vis": {"min": 0, "max": 60, "palette": ["0b3d2e","f5d76e","a93226"]}, "freshness": "REFERENCE", "resolution_m": 30},
    "srtm_aspect": {"dataset": "USGS/SRTMGL1_003", "kind": "terrain", "band": "aspect", "vis": {"min": 0, "max": 360, "palette": ["313695","74add1","ffffbf","f46d43","a50026"]}, "freshness": "REFERENCE", "resolution_m": 30},
    "wcmc_carbon_density": {"dataset": "WCMC/biomass_carbon_density/v1_0/2010", "kind": "image", "band": "carbon_tonnes_per_ha", "vis": {"min": 1, "max": 180, "palette": ["d9f0a3","78c679","238443","005a32"]}, "freshness": "REFERENCE", "resolution_m": 300},
    "wdpa_protected": {"dataset": "WCMC/WDPA/current/polygons", "kind": "feature_collection", "band": None, "vis": {"min": 0, "max": 1, "palette": ["2ed033"]}, "freshness": "REFERENCE", "resolution_m": None},
}

class EarthEngineAdapter:
    name = "google_earth_engine"
    source_url = "https://developers.google.com/earth-engine/datasets/"
    api_repo_url = "https://github.com/google/earthengine-api"

    def _ee(self):
        try:
            import ee
        except Exception as e:
            raise AdapterError("earthengine-api package is unavailable") from e
        try:
            # Uses Application Default Credentials or GOOGLE_APPLICATION_CREDENTIALS.
            ee.Initialize(project=settings.google_cloud_project or None)
        except Exception as e:
            raise AdapterError("Earth Engine is not authenticated. Configure GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_CLOUD_PROJECT.") from e
        return ee

    def catalog(self):
        return EE_LAYERS

    def health(self):
        """Validate the official Earth Engine Python API against the configured project.

        This makes a tiny server-side request. It never exposes credential material.
        """
        ee = self._ee()
        probe = ee.Number(1).getInfo()
        if probe != 1:
            raise AdapterError("Earth Engine authentication probe returned an unexpected result")
        return {
            "ok": True,
            "project": settings.google_cloud_project,
            "python_package": "earthengine-api",
            "official_repository": self.api_repo_url,
            "catalog_layers": len(EE_LAYERS),
        }

    def sample(self, layer_id: str, lat: float, lon: float, days: int = 3650):
        cfg = EE_LAYERS.get(layer_id)
        if not cfg:
            raise AdapterError(f"Unknown Earth Engine layer: {layer_id}")
        ee = self._ee()
        pt = ee.Geometry.Point([lon, lat])
        if cfg["kind"] == "feature_collection":
            fc = ee.FeatureCollection(cfg["dataset"]).filterBounds(pt).filter(ee.Filter.eq("PARENT_ISO", "IND"))
            feats = fc.limit(10).getInfo().get("features", [])
            rows=[]
            for f in feats:
                props=f.get("properties") or {}
                rows.append({k:props.get(k) for k in ("WDPAID","WDPA_PID","NAME","ORIG_NAME","DESIG_ENG","IUCN_CAT","STATUS","REP_AREA","GIS_AREA") if k in props})
            return {"layer_id":layer_id,"inside_protected_area":bool(rows),"matches":rows,"dataset":cfg["dataset"],"freshness":cfg["freshness"],"source":"Google Earth Engine / UNEP-WCMC WDPA"}
        if cfg["kind"] == "image":
            image = ee.Image(cfg["dataset"]).select(cfg["band"])
        elif cfg["kind"] == "terrain":
            terrain = ee.Terrain.products(ee.Image(cfg["dataset"]))
            image = terrain.select(cfg["band"])
        else:
            col = ee.ImageCollection(cfg["dataset"]).filterBounds(pt)
            if cfg.get("static_latest"):
                image = ee.Image(col.sort("system:time_start", False).first()).select(cfg["band"])
            else:
                end = datetime.now(timezone.utc)
                start = end - timedelta(days=max(1, min(days, 3650)))
                col = col.filterDate(start.isoformat(), end.isoformat())
                if cfg.get("quality") == "gedi_l4a":
                    def quality_mask(im):
                        return im.updateMask(im.select("l4_quality_flag").eq(1)).updateMask(im.select("degrade_flag").eq(0))
                    col = col.map(quality_mask)
                image = col.select(cfg["band"]).mean()
        scale = cfg["resolution_m"]
        val = image.reduceRegion(reducer=ee.Reducer.mean(), geometry=pt, scale=scale, bestEffort=True).get(cfg["band"]).getInfo()
        return {"layer_id":layer_id,"value":val,"band":cfg["band"],"dataset":cfg["dataset"],"resolution_m":scale,"freshness":cfg["freshness"],"source":"Google Earth Engine Data Catalog"}

    def tile(self, layer_id: str, lat: float | None = None, lon: float | None = None, days: int = 30):
        cfg = EE_LAYERS.get(layer_id)
        if not cfg:
            raise AdapterError(f"Unknown Earth Engine layer: {layer_id}")
        ee = self._ee()
        if cfg["kind"] == "feature_collection":
            fc = ee.FeatureCollection(cfg["dataset"]).filter(ee.Filter.eq("PARENT_ISO", "IND"))
            image = ee.Image().byte().paint(fc, 1).selfMask()
        elif cfg["kind"] == "image":
            image = ee.Image(cfg["dataset"]).select(cfg["band"])
        elif cfg["kind"] == "terrain":
            image = ee.Terrain.products(ee.Image(cfg["dataset"])).select(cfg["band"])
        else:
            col = ee.ImageCollection(cfg["dataset"])
            if lat is not None and lon is not None:
                col = col.filterBounds(ee.Geometry.Point([lon, lat]))
            if cfg.get("static_latest"):
                image = ee.Image(col.sort("system:time_start", False).first()).select(cfg["band"])
            else:
                end = datetime.now(timezone.utc)
                start = end - timedelta(days=max(1, min(days, 3650)))
                col = col.filterDate(start.isoformat(), end.isoformat())
                if cfg.get("quality") == "gedi_l4a":
                    def quality_mask(im):
                        return im.updateMask(im.select("l4_quality_flag").eq(1)).updateMask(im.select("degrade_flag").eq(0))
                    col = col.map(quality_mask)
                image = col.select(cfg["band"]).mean()
        info = image.getMapId(cfg["vis"])
        return {
            "layer_id": layer_id,
            "dataset": cfg["dataset"],
            "band": cfg["band"],
            "tile_url": info["tile_fetcher"].url_format,
            "freshness": cfg["freshness"],
            "resolution_m": cfg["resolution_m"],
            "source": "Google Earth Engine Data Catalog",
        }
