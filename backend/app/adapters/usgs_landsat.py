from __future__ import annotations
from datetime import datetime, timedelta, timezone
from app.adapters.base import BaseAdapter, AdapterError


class USGSLandsatAdapter(BaseAdapter):
    """Official USGS Landsat STAC discovery for the long historical archive."""

    name = "usgs_landsat"
    source_url = "https://landsatlook.usgs.gov/stac-server"
    collection = "landsat-c2l2-sr"

    async def search(self, lat: float, lon: float, start: datetime, end: datetime, limit: int = 100):
        body = {
            "collections": [self.collection],
            "datetime": f"{start.astimezone(timezone.utc).isoformat()}/{end.astimezone(timezone.utc).isoformat()}",
            "intersects": {"type": "Point", "coordinates": [lon, lat]},
            "limit": max(1, min(int(limit), 100)),
        }
        return await self.post_json(f"{self.source_url}/search", json=body)

    @staticmethod
    def _dt(item: dict) -> datetime | None:
        raw = (item.get("properties") or {}).get("datetime")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except Exception:
            return None

    @staticmethod
    def _cloud(item: dict) -> float | None:
        raw = (item.get("properties") or {}).get("eo:cloud_cover")
        try:
            return float(raw) if raw is not None else None
        except Exception:
            return None

    async def closest_scene(
        self,
        lat: float,
        lon: float,
        target_date: datetime,
        window_days: int = 35,
        cloud_lt: float = 60,
        max_window_days: int = 550,
    ) -> dict | None:
        # Landsat's older archive is much sparser than Sentinel-2. Expand only
        # when necessary and always return the real observation date + offset.
        windows=[]
        for days in (window_days, 90, 180, 365, max_window_days):
            days=max(3,min(int(days),int(max_window_days)))
            if days not in windows:
                windows.append(days)
        now=datetime.now(timezone.utc)
        last_error=None
        for days in windows:
            start=target_date-timedelta(days=days)
            end=min(now,target_date+timedelta(days=days+1))
            if start>=end:
                continue
            try:
                data=await self.search(lat,lon,start,end,100)
            except Exception as exc:
                last_error=exc
                continue
            candidates=[]
            for item in data.get("features") or []:
                observed=self._dt(item)
                if observed is None:
                    continue
                cloud=self._cloud(item)
                if cloud is not None and cloud>float(cloud_lt):
                    continue
                candidates.append((abs((observed-target_date).total_seconds()),observed,item))
            if candidates:
                _,observed,item=min(candidates,key=lambda row:row[0])
                item=dict(item)
                item["_vanrakshak_archive"]={
                    "requested_date":target_date.date().isoformat(),
                    "window_used_days":days,
                    "date_offset_days":round(abs((observed-target_date).total_seconds())/86400,1),
                    "cloud_filter":float(cloud_lt),
                }
                return item
        if last_error is not None:
            raise AdapterError(f"USGS Landsat archive unavailable: {last_error}") from last_error
        return None
