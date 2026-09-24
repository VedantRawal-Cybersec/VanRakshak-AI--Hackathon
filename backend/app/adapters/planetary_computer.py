from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings


class PlanetaryComputerAdapter(BaseAdapter):
    """Credential-free Microsoft Planetary Computer Sentinel-2 fallback.

    The STAC API is used for scene discovery. The public Planetary Computer
    Data API renders the selected real Sentinel-2 item, so VanRakshak can keep
    all scientific satellite modes available even when the primary Earth
    Search/TiTiler path is temporarily unavailable.
    """

    name = "planetary_computer"
    source_url = "https://planetarycomputer.microsoft.com/"
    tilejson_url = "https://planetarycomputer.microsoft.com/api/data/v1/item/WebMercatorQuad/tilejson.json"

    async def search_sentinel2(
        self,
        lat: float,
        lon: float,
        start: datetime,
        end: datetime,
        cloud_lt: float = 80,
        limit: int = 30,
    ):
        payload = {
            "collections": ["sentinel-2-l2a"],
            "bbox": [lon - 0.03, lat - 0.03, lon + 0.03, lat + 0.03],
            "datetime": f"{start.astimezone(timezone.utc).isoformat()}/{end.astimezone(timezone.utc).isoformat()}",
            "query": {"eo:cloud_cover": {"lt": float(cloud_lt)}},
            "limit": int(limit),
        }
        data = await self.post_json(
            settings.planetary_computer_stac_url.rstrip("/") + "/search",
            json=payload,
        )
        feats = data.get("features") or []
        feats.sort(
            key=lambda f: str((f.get("properties") or {}).get("datetime") or ""),
            reverse=True,
        )
        return {**data, "features": feats}

    async def latest_sentinel2(self, lat: float, lon: float, days: int = 45, cloud_lt: float = 80):
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        return await self.search_sentinel2(lat, lon, start, end, cloud_lt, 30)

    @staticmethod
    def _mode_params(mode: str):
        mode = mode.lower()
        common = [("collection", "sentinel-2-l2a"), ("tile_format", "png"), ("nodata", "0")]
        if mode == "true_color":
            return common + [
                ("assets", "B04"), ("assets", "B03"), ("assets", "B02"),
                ("rescale", "0,3000"),
                ("color_formula", "Gamma RGB 3.2 Saturation 0.9 Sigmoidal RGB 20 0.35"),
            ]
        if mode == "false_color":
            return common + [
                ("assets", "B08"), ("assets", "B04"), ("assets", "B03"),
                ("rescale", "0,4000"),
                ("color_formula", "Gamma RGB 3.0 Saturation 1.0 Sigmoidal RGB 20 0.35"),
            ]
        formulas = {
            "ndvi": (("B04", "B08"), "(B08-B04)/(B08+B04)", "rdylgn"),
            "ndmi": (("B08", "B11"), "(B08-B11)/(B08+B11)", "rdbu"),
            "nbr": (("B08", "B12"), "(B08-B12)/(B08+B12)", "rdylgn"),
            "ndwi": (("B03", "B08"), "(B03-B08)/(B03+B08)", "blues"),
        }
        if mode not in formulas:
            raise AdapterError(f"Unsupported Planetary Computer render mode: {mode}")
        assets, expression, cmap = formulas[mode]
        return common + [
            *(("assets", a) for a in assets),
            ("asset_as_band", "true"),
            ("expression", expression),
            ("rescale", "-1,1"),
            ("colormap_name", cmap),
        ]

    async def tile_spec(self, item: dict, mode: str = "true_color"):
        item_id = item.get("id")
        if not item_id:
            raise AdapterError("Planetary Computer item has no id")
        params = self._mode_params(mode)
        params.append(("item", item_id))
        tilejson = self.tilejson_url + "?" + urlencode(params, doseq=True, safe="(),/")
        data = await self.get_json(tilejson)
        tiles = data.get("tiles") or []
        if not tiles:
            raise AdapterError("Planetary Computer TileJSON returned no tile template")
        p = item.get("properties") or {}
        return {
            "mode": mode,
            "item_id": item_id,
            "observed_at": p.get("datetime"),
            "cloud_cover": p.get("eo:cloud_cover"),
            "tile_url": tiles[0],
            "tilejson_url": tilejson,
            "source": "Microsoft Planetary Computer / Sentinel-2 L2A Data API",
            "resolution_m": 10 if mode in {"true_color", "false_color", "ndvi", "ndwi"} else 20,
            "fallback_used": True,
            "attribution": "Copernicus Sentinel data via Microsoft Planetary Computer",
        }

    async def true_color_tile(self, item: dict):
        return await self.tile_spec(item, "true_color")
