from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable

from app.config import settings


async def _probe(name: str, coro: Awaitable[Any] | None, *, configured: bool = True, note: str | None = None):
    if not configured:
        close = getattr(coro, "close", None)
        if callable(close):
            close()
        return {"source": name, "status": "NOT_CONFIGURED", "ok": False, "latency_ms": None, "detail": note}
    started = time.perf_counter()
    try:
        data = await coro  # type: ignore[arg-type]
        latency = round((time.perf_counter() - started) * 1000, 1)
        return {"source": name, "status": "OK", "ok": True, "latency_ms": latency, "detail": None, "sample_available": data is not None}
    except Exception as exc:
        latency = round((time.perf_counter() - started) * 1000, 1)
        return {"source": name, "status": "ERROR", "ok": False, "latency_ms": latency, "detail": str(exc)}


async def snapshot(adapters: dict[str, Any], lat: float = 12.9716, lon: float = 77.5946):
    checks = [
        _probe("Copernicus STAC", adapters["copernicus"].latest_sentinel2(lat, lon, 14, 80)),
        _probe("Earth Search", adapters["earth"].latest_sentinel2(lat, lon, 14, 80)),
        _probe("Open-Meteo", adapters["weather"].current(lat, lon)),
        _probe("SoilGrids", adapters["soil"].point(lat, lon)),
        _probe("Nominatim", adapters["geocoder"].reverse(lat, lon)),
        _probe("Sentinel-1 ASF", adapters["s1"].latest(lat, lon, 14, 3)),
        _probe(
            "NASA FIRMS",
            adapters["firms"].fires(lat, lon),
            configured=bool(settings.firms_map_key),
            note="FIRMS key not configured. VanRakshak automatically uses EONET/GIBS context as a no-key fallback.",
        ),
        _probe(
            "Protected Planet",
            adapters["pp"].india(1),
            configured=bool(settings.protected_planet_token),
            note="Protected Planet token not configured. OSM protected-area context remains available.",
        ),
        _probe(
            "Google Earth Engine",
            asyncio.to_thread(adapters["ee"].health),
            configured=bool(settings.google_cloud_project),
            note="Earth Engine is optional; public GFW/Sentinel/NASA fallbacks remain available.",
        ),
    ]
    if "gibs" in adapters:
        checks.append(_probe("NASA GIBS", adapters["gibs"].health()))
    if "eonet" in adapters:
        checks.append(_probe("NASA EONET", adapters["eonet"].events(lat, lon, days=2, radius_deg=3, limit=1)))
    if "photon" in adapters:
        checks.append(_probe("Photon Geocoder", adapters["photon"].search("Bengaluru", 1)))
    if "power" in adapters:
        checks.append(_probe("NASA POWER", adapters["power"].health()))
    if "pc" in adapters:
        checks.append(_probe("Planetary Computer", adapters["pc"].latest_sentinel2(lat, lon, 30, 80)))
    if "metno" in adapters:
        checks.append(_probe("MET Norway", adapters["metno"].current(lat, lon)))
    if "gnews" in adapters:
        checks.append(_probe("Google News RSS", adapters["gnews"].forest_news("India forest", "1week", 3)))

    rows = await asyncio.gather(*checks)
    configured = [r for r in rows if r["status"] != "NOT_CONFIGURED"]
    ok_count = sum(1 for r in configured if r["ok"])
    return {
        "ok": bool(configured) and ok_count == len(configured),
        "configured_sources": len(configured),
        "healthy_sources": ok_count,
        "sources": rows,
        "fallback_ready": {
            "fire": any(r["source"] in {"NASA EONET","NASA GIBS"} and r["ok"] for r in rows),
            "geocoding": any(r["source"] in {"Nominatim","Photon Geocoder"} and r["ok"] for r in rows),
            "satellite": any(r["source"] in {"Earth Search","Copernicus STAC","NASA GIBS","Planetary Computer"} and r["ok"] for r in rows),
            "weather": any(r["source"] in {"Open-Meteo","MET Norway"} and r["ok"] for r in rows),
            "climate_history": any(r["source"] in {"Open-Meteo","NASA POWER"} and r["ok"] for r in rows),
            "news": any(r["source"] == "Google News RSS" and r["ok"] for r in rows),
        },
        "note": "Health is operational telemetry only. Missing credential-gated sources do not disable their credential-free fallbacks.",
    }
