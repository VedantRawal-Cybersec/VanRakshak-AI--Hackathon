from __future__ import annotations
from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings

class OverpassAdapter(BaseAdapter):
    name = "overpass"
    source_url = "https://www.openstreetmap.org/"

    @staticmethod
    def endpoints() -> list[str]:
        candidates = [
            settings.overpass_url,
            "https://overpass.private.coffee/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
        ]
        seen=set()
        out=[]
        for url in candidates:
            value=(url or "").strip().rstrip("/")
            if value and value not in seen:
                seen.add(value)
                out.append(value)
        return out

    async def _query(self, q: str):
        errors=[]
        for endpoint in self.endpoints():
            try:
                return await self.post_json(endpoint, data={"data": q})
            except Exception as exc:
                errors.append(f"{endpoint}: {exc}")
        raise AdapterError("all Overpass endpoints unavailable: " + " | ".join(errors))

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
