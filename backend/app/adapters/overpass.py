from __future__ import annotations
from app.adapters.base import BaseAdapter
from app.config import settings

class OverpassAdapter(BaseAdapter):
    name = "overpass"
    source_url = "https://www.openstreetmap.org/"

    async def _query(self, q: str):
        return await self.post_json(settings.overpass_url, data={"data": q})

    async def pressure(self, lat: float, lon: float, radius_m: int = 5000):
        q = f'''[out:json][timeout:20];(
          way(around:{radius_m},{lat},{lon})[highway];
          node(around:{radius_m},{lat},{lon})[place~"village|town|city|hamlet"];
          way(around:{radius_m},{lat},{lon})[landuse~"industrial|quarry|construction"];
          node(around:{radius_m},{lat},{lon})[man_made="mineshaft"];
        );out center tags;'''
        return await self._query(q)

    async def containing_protected_areas(self, lat: float, lon: float):
        # Overpass area index lets us query boundaries that actually contain the point.
        q=f'''[out:json][timeout:25];
        is_in({lat},{lon})->.containing;
        (
          area.containing[boundary="protected_area"];
          area.containing[leisure="nature_reserve"];
          area.containing[protect_class];
        );
        out center tags;'''
        return await self._query(q)
