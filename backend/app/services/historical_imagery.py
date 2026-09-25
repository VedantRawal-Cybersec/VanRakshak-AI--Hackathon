from __future__ import annotations
import asyncio
from datetime import datetime, timedelta, timezone
from app.adapters.base import AdapterError

ARCHIVE_START=datetime(1982,8,22,tzinfo=timezone.utc)
SENTINEL_START=datetime(2015,6,23,tzinfo=timezone.utc)


def normalize_date(value: datetime) -> datetime:
    if value.tzinfo is None:
        value=value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def validate_date(value: datetime, *, name: str):
    value=normalize_date(value)
    now=datetime.now(timezone.utc)+timedelta(days=1)
    if value < ARCHIVE_START:
        raise ValueError(f"{name} predates the supported Landsat archive ({ARCHIVE_START.date().isoformat()})")
    if value > now:
        raise ValueError(f"{name} is in the future")
    return value


def _observed(item: dict) -> str | None:
    return (item.get("properties") or {}).get("datetime")


def _closest(features: list[dict], target: datetime):
    def key(item):
        raw=_observed(item)
        try:
            observed=datetime.fromisoformat(str(raw).replace("Z","+00:00"))
            return abs((observed-target).total_seconds())
        except Exception:
            return float("inf")
    return min(features,key=key) if features else None


async def _public_landsat_scene(usgs,gcp,lat,lon,target,mode,window_days,cloud_lt):
    if usgs is None or gcp is None:
        return None
    item=await usgs.closest_scene(lat,lon,target,window_days,cloud_lt)
    if not item:
        return None
    product=await gcp.resolve_item(item)
    if not product:
        return None
    return gcp.tile_spec(item,product,mode,target.date().isoformat())


async def _planetary_scene(pc,lat,lon,target,mode,window_days,cloud_lt,collection):
    if pc is None:
        return None
    start=target-timedelta(days=window_days)
    end=min(datetime.now(timezone.utc),target+timedelta(days=window_days+1))
    if start>=end:
        return None
    data=await pc.search_optical(lat,lon,start,end,cloud_lt,80,collection)
    item=_closest(data.get("features") or [],target)
    if not item:
        return None
    spec=await pc.tile_spec(item,mode)
    spec["requested_date"]=target.date().isoformat()
    try:
        actual=datetime.fromisoformat(str(spec.get("observed_at") or "").replace("Z","+00:00"))
        spec["date_offset_days"]=round(abs((actual-target).total_seconds())/86400,1)
    except Exception:
        pass
    return spec


async def dated_scene(earth,pc,lat,lon,target_date,mode="true_color",window_days=35,cloud_lt=60,usgs=None,gcp=None):
    target_date=validate_date(target_date,name="date")
    errors=[]

    if target_date >= SENTINEL_START:
        try:
            item=await earth.closest_scene(lat,lon,target_date,window_days,cloud_lt) if earth is not None else None
            if item:
                spec=earth.tile_spec(item,mode)
                spec["requested_date"]=target_date.date().isoformat()
                try:
                    actual=datetime.fromisoformat(str(spec.get("observed_at") or "").replace("Z","+00:00"))
                    spec["date_offset_days"]=round(abs((actual-target_date).total_seconds())/86400,1)
                except Exception:
                    pass
                return spec
        except Exception as exc:
            errors.append(f"Earth Search Sentinel-2: {exc}")
        try:
            spec=await _planetary_scene(pc,lat,lon,target_date,mode,window_days,cloud_lt,"sentinel-2-l2a")
            if spec:
                if errors: spec["provider_trace"]=errors
                return spec
        except Exception as exc:
            errors.append(f"Planetary Computer Sentinel-2: {exc}")

    try:
        spec=await _public_landsat_scene(usgs,gcp,lat,lon,target_date,mode,window_days,cloud_lt)
        if spec:
            if errors: spec["provider_trace"]=errors
            return spec
    except Exception as exc:
        errors.append(f"USGS/Google public Landsat: {exc}")

    try:
        fallback_window=max(window_days,180 if target_date.year<2000 else window_days)
        spec=await _planetary_scene(pc,lat,lon,target_date,mode,min(550,fallback_window),cloud_lt,"landsat-c2-l2")
        if spec:
            if errors: spec["provider_trace"]=errors
            return spec
    except Exception as exc:
        errors.append(f"Planetary Computer Landsat: {exc}")

    if errors and all("no " not in e.lower() for e in errors):
        raise AdapterError("Historical imagery providers unavailable: "+" | ".join(errors))
    return None


async def compare(earth,pc,lat,lon,before_date,after_date,mode="true_color",window_days=35,cloud_lt=60,usgs=None,gcp=None):
    before_date=validate_date(before_date,name="before_date")
    after_date=validate_date(after_date,name="after_date")
    if after_date <= before_date:
        raise ValueError("after_date must be later than before_date")
    before,after=await asyncio.gather(
        dated_scene(earth,pc,lat,lon,before_date,mode,window_days,cloud_lt,usgs,gcp),
        dated_scene(earth,pc,lat,lon,after_date,mode,window_days,cloud_lt,usgs,gcp),
    )
    if not before or not after:
        return None
    before_obs=before.get("observed_at") or ""
    after_obs=after.get("observed_at") or ""
    if before.get("item_id") == after.get("item_id") or (before_obs and after_obs and before_obs >= after_obs):
        raise ValueError("The selected dates resolve to the same or reversed satellite observation. Pick dates farther apart.")
    return {
        "before":before,"after":after,"mode":mode,"label":"HISTORICAL",
        "requested":{"before":before_date.date().isoformat(),"after":after_date.date().isoformat()},
        "warning":"Displayed dates are actual satellite capture dates. Sparse historical archives may automatically use the nearest available Landsat observation and report the offset explicitly.",
    }


async def timeline(earth,pc,lat,lon,start,end,cloud_lt=60,limit=50,usgs=None,gcp=None):
    start=validate_date(start,name="start")
    end=validate_date(end,name="end")
    if end <= start:
        raise ValueError("end must be after start")
    count=max(2,min(int(limit),12))
    span=end-start
    targets=[start + span*(i/(count-1)) for i in range(count)]

    semaphore=asyncio.Semaphore(3)
    async def load(target):
        async with semaphore:
            return await dated_scene(earth,pc,lat,lon,target,"true_color",45,cloud_lt,usgs,gcp)

    results=await asyncio.gather(*(load(target) for target in targets),return_exceptions=True)
    rows=[]; errors=[]; seen=set()
    for target,result in zip(targets,results):
        if isinstance(result,Exception):
            errors.append({"requested_date":target.date().isoformat(),"error":str(result)})
            continue
        if not result:
            continue
        key=result.get("item_id") or result.get("observed_at")
        if key in seen:
            continue
        seen.add(key); rows.append(result)
    rows.sort(key=lambda row:row.get("observed_at") or "")
    return {
        "scenes":rows,"count":len(rows),"errors":errors,"label":"HISTORICAL",
        "source":"Mixed Sentinel-2 / USGS Landsat archive with credential-free public raster mirrors",
        "requested_range":{"start":start.date().isoformat(),"end":end.date().isoformat()},
    }
