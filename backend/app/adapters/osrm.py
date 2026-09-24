from __future__ import annotations
from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings

class OSRMAdapter(BaseAdapter):
    name = "osrm"
    source_url = "https://router.project-osrm.org"

    async def route(self, points: list[tuple[float,float]]):
        if len(points) < 2:
            raise AdapterError("At least two points are required")
        coords = ";".join(f"{lon},{lat}" for lat,lon in points)
        url = f"{settings.osrm_url.rstrip('/')}/route/v1/driving/{coords}"
        data = await self.get_json(url, params={"overview":"full","geometries":"geojson","steps":"false"})
        routes = data.get("routes") or []
        if not routes:
            raise AdapterError(data.get("message") or "OSRM returned no route")
        r = routes[0]
        return {"distance_km": round(r.get("distance",0)/1000,2), "duration_min": round(r.get("duration",0)/60,1), "geometry": r.get("geometry"), "source":"OSRM/OpenStreetMap"}
