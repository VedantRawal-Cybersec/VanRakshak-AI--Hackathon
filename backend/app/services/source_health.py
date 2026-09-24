from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable

from app.config import settings


async def _probe(name: str, coro: Awaitable[Any] | None, *, configured: bool = True, note: str | None = None):
    if not configured:
        # snapshot() may receive an already-created coroutine for a credential-gated
        # provider. Explicitly close it so CI/runtime never leak un-awaited coroutines.
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
    """Return a non-fabricated provider-health snapshot.

    Public providers are actually queried. Credential-gated providers are marked NOT_CONFIGURED
    rather than being treated as failures. The endpoint is intended for command-center health UI,
    not environmental science or alert scoring.
    """
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
            note="Set FIRMS_MAP_KEY to enable NRT fire health checks.",
        ),
        _probe(
            "Protected Planet",
            adapters["pp"].india(1),
            configured=bool(settings.protected_planet_token),
            note="Set PROTECTED_PLANET_TOKEN to enable API v4 health checks.",
        ),
    ]
    rows = await asyncio.gather(*checks)
    configured = [r for r in rows if r["status"] != "NOT_CONFIGURED"]
    ok_count = sum(1 for r in configured if r["ok"])
    return {
        "ok": bool(configured) and ok_count == len(configured),
        "configured_sources": len(configured),
        "healthy_sources": ok_count,
        "sources": rows,
        "note": "Provider health is operational telemetry only. It does not imply that newest imagery exists for every AOI.",
    }
