from __future__ import annotations

from datetime import datetime, timedelta, timezone
from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings


class PlanetaryComputerAdapter(BaseAdapter):
    name = "planetary_computer"
    source_url = "https://planetarycomputer.microsoft.com/"

    async def search_sentinel2(self, lat: float, lon: float, start: datetime, end: datetime, cloud_lt: float = 80, limit: int = 30):
        payload={
            "collections":["sentinel-2-l2a"],
            "bbox":[lon-0.03,lat-0.03,lon+0.03,lat+0.03],
            "datetime":f"{start.astimezone(timezone.utc).isoformat()}/{end.astimezone(timezone.utc).isoformat()}",
            "query":{"eo:cloud_cover":{"lt":float(cloud_lt)}},
            "limit":int(limit),
        }
        data=await self.post_json(settings.planetary_computer_stac_url.rstrip("/")+"/search",json=payload)
        feats=data.get("features") or []
        feats.sort(key=lambda f:str((f.get("properties") or {}).get("datetime") or ""),reverse=True)
        return {**data,"features":feats}

    async def latest_sentinel2(self, lat: float, lon: float, days: int = 45, cloud_lt: float = 80):
        end=datetime.now(timezone.utc)
        start=end-timedelta(days=days)
        return await self.search_sentinel2(lat,lon,start,end,cloud_lt,30)

    async def true_color_tile(self, item: dict):
        assets=item.get("assets") or {}
        tilejson=assets.get("tilejson") or {}
        href=tilejson.get("href")
        if not href:
            raise AdapterError("Planetary Computer item has no TileJSON rendering asset")
        data=await self.get_json(href)
        tiles=data.get("tiles") or []
        if not tiles:
            raise AdapterError("Planetary Computer TileJSON returned no tile template")
        p=item.get("properties") or {}
        return {
            "mode":"true_color",
            "item_id":item.get("id"),
            "observed_at":p.get("datetime"),
            "cloud_cover":p.get("eo:cloud_cover"),
            "tile_url":tiles[0],
            "source":"Microsoft Planetary Computer / Sentinel-2 L2A Data API",
            "resolution_m":10,
            "fallback_used":True,
            "attribution":"Copernicus Sentinel data via Microsoft Planetary Computer",
        }
