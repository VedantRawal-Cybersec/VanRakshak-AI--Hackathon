from __future__ import annotations
import httpx
from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings

class OverpassAdapter(BaseAdapter):
    name = "overpass"
    source_url = "https://www.openstreetmap.org/"

    async def pressure(self, lat: float, lon: float, radius_m: int = 5000):
        q = f'''[out:json][timeout:20];(
          way(around:{radius_m},{lat},{lon})[highway];
          node(around:{radius_m},{lat},{lon})[place~"village|town|city|hamlet"];
          way(around:{radius_m},{lat},{lon})[landuse~"industrial|quarry|construction"];
          node(around:{radius_m},{lat},{lon})[man_made="mineshaft"];
        );out center tags;'''
        if not settings.allow_network:
            raise AdapterError("Network access disabled")
        async with httpx.AsyncClient(timeout=settings.request_timeout_s, follow_redirects=True, headers={"User-Agent":"VanRakshakAI/1.0"}) as client:
            r = await client.post(settings.overpass_url, data={"data": q})
            r.raise_for_status()
            return r.json()
