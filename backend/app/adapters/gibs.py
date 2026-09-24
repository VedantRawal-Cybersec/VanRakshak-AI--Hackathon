from __future__ import annotations
from datetime import date, timedelta
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
