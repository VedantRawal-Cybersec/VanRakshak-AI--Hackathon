from __future__ import annotations
from app.adapters.base import BaseAdapter
from app.config import settings

class EONETAdapter(BaseAdapter):
    name = "nasa_eonet"
    source_url = "https://eonet.gsfc.nasa.gov/"

    async def events(self, lat: float, lon: float, days: int = 30, radius_deg: float = 2.0, limit: int = 50):
        west, south, east, north = lon-radius_deg, lat-radius_deg, lon+radius_deg, lat+radius_deg
        params = {
            "status": "all",
            "days": max(1, min(days, 365)),
            "limit": max(1, min(limit, 200)),
            "bbox": f"{west},{south},{east},{north}",
        }
        return await self.get_json(settings.eonet_url.rstrip("/") + "/events", params=params)

    async def wildfire_points(self, lat: float, lon: float, days: int = 30, radius_deg: float = 2.0):
        data = await self.events(lat, lon, days=days, radius_deg=radius_deg)
        rows = []
        for event in data.get("events") or []:
            cats = [str((c or {}).get("title") or (c or {}).get("id") or "").lower() for c in event.get("categories") or []]
            if not any("wildfire" in c or c == "8" for c in cats):
                continue
            geoms = event.get("geometry") or []
            if not geoms:
                continue
            g = geoms[-1]
            coords = g.get("coordinates") or []
            if g.get("type") != "Point" or len(coords) < 2:
                continue
            rows.append({
                "latitude": coords[1],
                "longitude": coords[0],
                "acq_date": str(g.get("date") or "")[:10],
                "acq_time": str(g.get("date") or "")[11:16].replace(":", ""),
                "satellite": "EONET_CONTEXT",
                "confidence": "context",
                "frp": None,
                "daynight": None,
                "event_id": event.get("id"),
                "event_title": event.get("title"),
                "_firms_source": "NASA_EONET_WILDFIRE_CONTEXT",
            })
        return rows
