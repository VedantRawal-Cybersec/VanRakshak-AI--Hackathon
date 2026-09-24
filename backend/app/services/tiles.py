from __future__ import annotations
from datetime import datetime, timedelta, timezone
from app.adapters.base import AdapterError
from app.adapters.earth_search import EarthSearchAdapter
from app.adapters.gfw import GFWAdapter

async def satellite_layer(earth: EarthSearchAdapter, lat: float, lon: float, mode: str, days: int, cloud_lt: float, start: datetime | None = None, end: datetime | None = None):
    if start is not None or end is not None:
        end = end or datetime.now(timezone.utc)
        start = start or (end - timedelta(days=days))
        if start >= end:
            raise AdapterError("Satellite filter start date must be before end date")
        data = await earth.search(lat, lon, start, end, "sentinel-2-l2a", cloud_lt, 60)
    else:
        data = await earth.latest_sentinel2(lat, lon, days=days, cloud_lt=cloud_lt)
    features = data.get("features", [])
    if not features:
        raise AdapterError("No suitable Sentinel-2 L2A scene found for this location/time/cloud filter")
    # Prefer the newest scene that already satisfies the cloud threshold.
    # Cloud cover is only the tie-breaker, so "latest" really means latest.
    def key(f):
        p=f.get("properties") or {}
        raw=str(p.get("datetime") or "")
        try:
            ts=datetime.fromisoformat(raw.replace("Z","+00:00")).timestamp()
        except Exception:
            ts=0.0
        cloud=p.get("eo:cloud_cover")
        return (-ts,float(cloud if cloud is not None else 1000))
    item = sorted(features, key=key)[0]
    return earth.tile_spec(item, mode)

async def compare_layers(earth: EarthSearchAdapter, lat: float, lon: float, before_date: datetime, after_date: datetime, mode: str, window_days: int, cloud_lt: float):
    before = await earth.closest_scene(lat, lon, before_date, window_days, cloud_lt)
    after = await earth.closest_scene(lat, lon, after_date, window_days, cloud_lt)
    if not before or not after:
        raise AdapterError("Could not find suitable scenes for both comparison dates")
    return {"before": earth.tile_spec(before, mode), "after": earth.tile_spec(after, mode)}

def gfw_layer(gfw: GFWAdapter, dataset: str, start_date: str | None, end_date: str | None, confidence: str):
    return gfw.tile_layer(dataset=dataset, start_date=start_date, end_date=end_date, confidence=confidence)
