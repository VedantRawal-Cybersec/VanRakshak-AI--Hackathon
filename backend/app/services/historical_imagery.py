"""Dated imagery selection; never replace an unavailable archive with today's map."""
from datetime import datetime, timedelta, timezone
import asyncio
from app.adapters.base import AdapterError

ARCHIVE_START = datetime(1982, 8, 22, tzinfo=timezone.utc)
SENTINEL_START = datetime(2015, 6, 23, tzinfo=timezone.utc)


def validate_dates(start, end):
    if start < ARCHIVE_START:
        raise ValueError("The supported Landsat archive starts on 1982-08-22.")
    if start >= end:
        raise ValueError("The before/start date must be earlier than the after/end date.")
    if end.date() > datetime.now(timezone.utc).date():
        raise ValueError("Satellite observations cannot use future dates; forecasts are a separate estimate.")


async def dated_scene(earth, pc, lat, lon, target, mode, window, cloud):
    start = max(ARCHIVE_START, target - timedelta(days=window))
    end = min(datetime.now(timezone.utc), target + timedelta(days=window + 1))
    errors = []
    if target >= SENTINEL_START:
        try:
            scene = await earth.closest_scene(lat, lon, target, window, cloud)
            if scene:
                return {**earth.tile_spec(scene, mode), "requested_date": target.date().isoformat()}
        except AdapterError as exc:
            errors.append(str(exc))
    collection = "landsat-c2-l2" if target < SENTINEL_START else "sentinel-2-l2a"
    try:
        data = await pc.search_optical(lat, lon, start, end, cloud, 100, collection)
        items = data.get("features") or []
        items = [i for i in items if (i.get("properties") or {}).get("datetime")]
        items.sort(key=lambda i: abs((datetime.fromisoformat(i["properties"]["datetime"].replace("Z", "+00:00")) - target).total_seconds()))
        if items:
            spec = await pc.tile_spec(items[0], mode)
            return {**spec, "requested_date": target.date().isoformat()}
    except AdapterError as exc:
        errors.append(str(exc))
    if errors:
        raise AdapterError("Historical imagery provider unavailable: " + "; ".join(errors))
    return None


async def compare(earth, pc, lat, lon, before, after, mode, window, cloud):
    validate_dates(before, after)
    b, a = await asyncio.gather(
        dated_scene(earth, pc, lat, lon, before, mode, window, cloud),
        dated_scene(earth, pc, lat, lon, after, mode, window, cloud),
    )
    if not b or not a:
        return None
    if b.get("item_id") == a.get("item_id") or b["observed_at"] >= a["observed_at"]:
        raise ValueError("The selected windows resolve to the same or reversed observations. Choose dates farther apart.")
    return {"before": b, "after": a, "note": "Actual capture dates are shown. Landsat is 30 m; Sentinel-2 is 10–20 m. Cross-sensor appearance is not a quantitative deforestation measurement."}


async def timeline(earth, pc, lat, lon, start, end, cloud, limit):
    validate_dates(start, end)
    collection = "landsat-c2-l2" if start < SENTINEL_START else "sentinel-2-l2a"
    # For long histories, sample bounded date windows across the entire range,
    # rather than displaying only the first page of the most recent scenes.
    count = min(limit, 12)
    step = (end - start) / count
    async def sample(i):
        left, right = start + step * i, start + step * (i + 1)
        data = await pc.search_optical(lat, lon, left, right, cloud, 1, collection)
        items = data.get("features") or []
        if not items:
            return None
        item = items[0]
        spec = await pc.tile_spec(item, "true_color")
        return {**spec, "id": item["id"], "datetime": spec["observed_at"]}
    rows = []
    errors = []
    # Keep provider concurrency bounded.
    for offset in range(0, count, 3):
        for result in await asyncio.gather(*(sample(i) for i in range(offset, min(offset + 3, count))), return_exceptions=True):
            if isinstance(result, Exception):
                errors.append(str(result))
            elif result:
                rows.append(result)
    if not rows and errors:
        raise AdapterError("Timeline imagery unavailable: " + errors[0])
    scenes = sorted({r["id"]: r for r in rows}.values(), key=lambda r: r["datetime"])
    return {"count": len(scenes), "scenes": scenes, "source": "Microsoft Planetary Computer", "label": "HISTORICAL", "sampled": True, "warnings": errors}
