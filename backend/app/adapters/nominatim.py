from __future__ import annotations
from app.adapters.base import BaseAdapter
from app.config import settings

class NominatimAdapter(BaseAdapter):
    name = "nominatim"
    source_url = "https://nominatim.openstreetmap.org"

    async def search(self, q: str, limit: int = 5):
        params = {"q": q, "format": "jsonv2", "limit": min(max(limit, 1), 10), "countrycodes": "in", "addressdetails": 1, "polygon_geojson": 1}
        return await self.get_json(settings.nominatim_url.rstrip("/") + "/search", params=params)

    async def reverse(self, lat: float, lon: float):
        params = {"lat": lat, "lon": lon, "format": "jsonv2", "addressdetails": 1, "zoom": 12}
        return await self.get_json(settings.nominatim_url.rstrip("/") + "/reverse", params=params)
