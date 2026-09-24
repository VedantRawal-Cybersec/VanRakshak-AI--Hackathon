from __future__ import annotations
from datetime import datetime, timedelta, timezone
import httpx
from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings

class CopernicusAdapter(BaseAdapter):
    name = "copernicus_stac"
    source_url = "https://dataspace.copernicus.eu/"

    async def latest_sentinel2(self, lat: float, lon: float, days: int = 30, cloud_lt: float = 40):
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        body = {
            "collections": ["sentinel-2-l2a"],
            "datetime": f"{start.isoformat()}/{end.isoformat()}",
            "intersects": {"type":"Point","coordinates":[lon,lat]},
            "query": {"eo:cloud_cover": {"lt": cloud_lt}},
            "sortby": [{"field":"properties.datetime","direction":"desc"}],
            "limit": 5,
        }
        if not settings.allow_network:
            raise AdapterError("Network access disabled")
        async with httpx.AsyncClient(timeout=settings.request_timeout_s, follow_redirects=True, headers={"User-Agent":"VanRakshakAI/1.0"}) as client:
            r = await client.post(f"{settings.copernicus_stac_url}/search", json=body)
            r.raise_for_status()
            return r.json()
