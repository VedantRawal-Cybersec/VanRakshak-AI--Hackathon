from __future__ import annotations
from datetime import datetime, timedelta, timezone
from app.adapters.base import BaseAdapter

class Sentinel1ASFAdapter(BaseAdapter):
    name = "sentinel1_asf"
    source_url = "https://api.daac.asf.alaska.edu/services/search/param"

    async def latest(self, lat: float, lon: float, days: int = 30, max_results: int = 10):
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=max(1, min(days, 365)))
        params = {
            "dataset": "SENTINEL-1",
            "intersectsWith": f"POINT ({lon} {lat})",
            "start": start.isoformat().replace("+00:00", "Z"),
            "end": end.isoformat().replace("+00:00", "Z"),
            "output": "geojson",
            "maxResults": min(max(max_results, 1), 50),
        }
        return await self.get_json(self.source_url, params=params)
