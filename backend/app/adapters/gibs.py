from __future__ import annotations
from datetime import date, timedelta
from urllib.parse import urlencode
from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings

class GIBSAdapter(BaseAdapter):
    name = "nasa_gibs"
    source_url = "https://gibs.earthdata.nasa.gov/"

    # Only layers with a verified Web-Mercator REST tile pattern are exposed here.
    LAYERS = {
        "modis_terra_true_color": {
            "identifier": "MODIS_Terra_CorrectedReflectance_TrueColor",
            "label": "MODIS Terra True Color",
            "format": "jpg",
            "matrix": "GoogleMapsCompatible_Level9",
            "max_zoom": 9,
        },
        "modis_aqua_true_color": {
            "identifier": "MODIS_Aqua_CorrectedReflectance_TrueColor",
            "label": "MODIS Aqua True Color",
            "format": "jpg",
            "matrix": "GoogleMapsCompatible_Level9",
            "max_zoom": 9,
        },
        "viirs_snpp_true_color": {
            "identifier": "VIIRS_SNPP_CorrectedReflectance_TrueColor",
            "label": "VIIRS S-NPP True Color",
            "format": "jpeg", "service": "wms", "max_zoom": 9, "resolution_m": 250,
        },
        "viirs_snpp_thermal_anomalies": {
            "identifier": "VIIRS_SNPP_Thermal_Anomalies_375m_All",
            "label": "VIIRS S-NPP Thermal Anomalies 375 m",
            "format": "png", "service": "wms", "max_zoom": 10, "resolution_m": 375,
        },
        "modis_terra_ndvi_8day": {
            "identifier": "MODIS_Terra_NDVI_8Day",
            "label": "MODIS Terra NDVI 8-Day",
            "format": "png", "service": "wms", "max_zoom": 9, "resolution_m": 250,
        },
        "modis_terra_lst_day": {
            "identifier": "MODIS_Terra_Land_Surface_Temp_Day",
            "label": "MODIS Terra Land Surface Temperature Day",
            "format": "png", "service": "wms", "max_zoom": 8, "resolution_m": 1000,
        },
        "imerg_precipitation_rate": {
            "identifier": "IMERG_Precipitation_Rate",
            "label": "GPM IMERG Precipitation Rate",
            "format": "png", "service": "wms", "max_zoom": 7, "resolution_m": 10000,
        },
        "hls_ndvi_sentinel": {
            "identifier": "HLS_NDVI_Sentinel",
            "label": "HLS Sentinel NDVI",
            "format": "png", "service": "wms", "max_zoom": 12, "resolution_m": 30,
        },
        "hls_ndwi_sentinel": {
            "identifier": "HLS_NDWI_Sentinel",
            "label": "HLS Sentinel NDWI",
            "format": "png", "service": "wms", "max_zoom": 12, "resolution_m": 30,
        },
        "hls_moisture_sentinel": {
            "identifier": "HLS_Moisture_Index_Sentinel",
            "label": "HLS Sentinel Moisture Index",
            "format": "png", "service": "wms", "max_zoom": 12, "resolution_m": 30,
        },
        "hls_nbr_sentinel": {
            "identifier": "HLS_NBR_Sentinel",
            "label": "HLS Sentinel NBR",
            "format": "png", "service": "wms", "max_zoom": 12, "resolution_m": 30,
        },
        "viirs_snpp_false_color": {
            "identifier": "VIIRS_SNPP_CorrectedReflectance_BandsM11-I2-I1",
            "label": "VIIRS S-NPP False Color",
            "format": "jpeg", "service": "wms", "max_zoom": 9, "resolution_m": 250,
        },
    }

    def catalog(self):
        return [{"id": k, **v, "source": "NASA Earthdata GIBS", "auth_required": False} for k,v in self.LAYERS.items()]

    def tile_spec(self, layer_id: str, observed_date: str | None = None):
        layer = self.LAYERS.get(layer_id)
        if not layer:
            raise AdapterError(f"Unsupported GIBS layer: {layer_id}")
        d = observed_date or (date.today() - timedelta(days=1)).isoformat()
        # Avoid accepting arbitrary path fragments.
        try:
            parsed = date.fromisoformat(d)
        except ValueError as exc:
            raise AdapterError("GIBS date must use YYYY-MM-DD") from exc
        # Daily imagery can lag UTC day boundaries; never default a map tile to an incomplete future/today slot.
        if parsed >= date.today():
            parsed = date.today() - timedelta(days=1)
            d = parsed.isoformat()
        base = settings.gibs_url.rstrip("/")
        if layer.get("service") == "wms":
            params=[
                ("SERVICE","WMS"),("REQUEST","GetMap"),("VERSION","1.1.1"),
                ("LAYERS",layer["identifier"]),("STYLES",""),
                ("FORMAT","image/"+layer["format"]),("TRANSPARENT","TRUE"),
                ("HEIGHT","256"),("WIDTH","256"),("SRS","EPSG:3857"),
                ("BBOX","{bbox-epsg-3857}"),("TIME",d),
            ]
            url=base+"/wms/epsg3857/best/wms.cgi?"+urlencode(params,safe="{},:")
        else:
            url = (
                f"{base}/wmts/epsg3857/best/{layer['identifier']}/default/{d}/"
                f"{layer['matrix']}/{{z}}/{{y}}/{{x}}.{layer['format']}"
            )
        return {
            "layer_id": layer_id,
            "identifier": layer["identifier"],
            "label": layer["label"],
            "date": d,
            "tile_url": url,
            "max_zoom": layer["max_zoom"],
            "resolution_m": layer.get("resolution_m"),
            "service": layer.get("service","wmts"),
            "source": "NASA Earthdata GIBS",
            "freshness": "DYNAMIC_RECENT",
            "auth_required": False,
            "attribution": "NASA EOSDIS Worldview / GIBS",
        }

    async def health(self):
        url = settings.gibs_url.rstrip("/") + "/wmts/epsg3857/best/1.0.0/WMTSCapabilities.xml"
        text = await self.get_text(url)
        if "Capabilities" not in text and "WMTS" not in text:
            raise AdapterError("NASA GIBS returned an unexpected capabilities document")
        return {"ok": True, "service": "NASA GIBS WMTS"}
