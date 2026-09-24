from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from celery import Celery
from app.config import settings
from app.adapters import CopernicusAdapter, OpenMeteoAdapter, FIRMSAdapter

celery = Celery("vanrakshak", broker=settings.redis_url, backend=settings.redis_url)
celery.conf.timezone = "UTC"
celery.conf.beat_schedule = {
    "source-health-every-15-min": {"task": "vanrakshak.source_health", "schedule": 900.0},
}


def _run(coro):
    return asyncio.run(coro)


def _persist(rows: dict[str, object]):
    try:
        from app.db import SessionLocal, SourceHealthRecord
        with SessionLocal() as db:
            for source, value in rows.items():
                ok = value is True
                detail = None if ok else str(value)
                db.add(SourceHealthRecord(source=source, ok="true" if ok else "false", detail=detail))
            db.commit()
    except Exception:
        # Scheduler must never fail solely because persistence is temporarily unavailable.
        pass


@celery.task(name="vanrakshak.source_health")
def source_health():
    lat, lon = 12.9716, 77.5946
    out: dict[str, object] = {}

    async def checks():
        c = CopernicusAdapter(); w = OpenMeteoAdapter(); f = FIRMSAdapter()
        try: out["copernicus"] = bool((await c.latest_sentinel2(lat, lon, 14, 80)).get("features") is not None)
        except Exception as e: out["copernicus"] = str(e)
        try: out["weather"] = bool((await w.current(lat, lon)).get("current") is not None)
        except Exception as e: out["weather"] = str(e)
        if settings.firms_map_key:
            try: out["firms"] = isinstance(await f.fires(lat, lon), list)
            except Exception as e: out["firms"] = str(e)
        else:
            out["firms"] = "not_configured"

    _run(checks())
    _persist(out)
    return {"checked_at": datetime.now(timezone.utc).isoformat(), "sources": out}
