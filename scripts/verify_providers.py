from __future__ import annotations

import asyncio
import json
import os
import sys

# Run from repository root:
#   PYTHONPATH=backend python scripts/verify_providers.py
#
# This script never prints secret values. It only reports whether providers
# are configured and whether a minimal live request succeeds.

from app.adapters import FIRMSAdapter, EarthEngineAdapter


async def check_firms():
    configured = bool(os.getenv("FIRMS_MAP_KEY", "").strip())
    if not configured:
        return {"provider": "NASA FIRMS", "configured": False, "ok": False, "detail": "FIRMS_MAP_KEY is not set"}
    try:
        rows = await FIRMSAdapter().fires(12.9716, 77.5946, days=1)
        return {
            "provider": "NASA FIRMS",
            "configured": True,
            "ok": True,
            "sample_count": len(rows),
            "detail": "Live API request succeeded",
        }
    except Exception as exc:
        return {"provider": "NASA FIRMS", "configured": True, "ok": False, "detail": str(exc)}


async def check_earth_engine():
    configured = bool(os.getenv("GOOGLE_CLOUD_PROJECT", "").strip())
    if not configured:
        return {
            "provider": "Google Earth Engine",
            "configured": False,
            "ok": False,
            "detail": "GOOGLE_CLOUD_PROJECT is not set",
        }
    try:
        data = await asyncio.to_thread(EarthEngineAdapter().health)
        return {"provider": "Google Earth Engine", "configured": True, "ok": True, "detail": data}
    except Exception as exc:
        return {"provider": "Google Earth Engine", "configured": True, "ok": False, "detail": str(exc)}


async def main():
    checks = await asyncio.gather(check_firms(), check_earth_engine())
    print(json.dumps({"providers": checks}, indent=2))
    failed = [x for x in checks if x["configured"] and not x["ok"]]
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
