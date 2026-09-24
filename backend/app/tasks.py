from __future__ import annotations
import asyncio
import hashlib
from datetime import datetime, timezone
from celery import Celery
from app.config import settings
from app.adapters import CopernicusAdapter, OpenMeteoAdapter, FIRMSAdapter, EONETAdapter
from app.services.fallbacks import fire_rows as fallback_fire_rows

celery = Celery("vanrakshak", broker=settings.redis_url, backend=settings.redis_url)
celery.conf.timezone = "UTC"
celery.conf.beat_schedule = {
    "source-health-every-15-min": {"task": "vanrakshak.source_health", "schedule": 900.0},
    "fire-context-every-30-min": {"task": "vanrakshak.fire_context", "schedule": 1800.0},
}

def _run(coro):
    return asyncio.run(coro)

def _persist_health(rows: dict[str, object]):
    try:
        from app.db import SessionLocal, SourceHealthRecord
        with SessionLocal() as db:
            for source, value in rows.items():
                ok = value is True
                detail = None if ok else str(value)
                db.add(SourceHealthRecord(source=source, ok="true" if ok else "false", detail=detail))
            db.commit()
    except Exception:
        pass

def _fire_fingerprint(row: dict) -> str:
    raw="|".join(str(row.get(k) or "") for k in ("latitude","longitude","acq_date","acq_time","satellite","event_id","_firms_source"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _persist_fire(rows: list[dict], source: str) -> int:
    try:
        from app.db import SessionLocal, FireObservationRecord
        inserted=0
        with SessionLocal() as db:
            for row in rows:
                try:
                    lat=float(row.get("latitude")); lon=float(row.get("longitude"))
                except Exception:
                    continue
                fp=_fire_fingerprint(row)
                if db.query(FireObservationRecord).filter_by(fingerprint=fp).first():
                    continue
                observed=" ".join(str(row.get(k) or "") for k in ("acq_date","acq_time")).strip() or None
                try: frp=float(row.get("frp")) if row.get("frp") not in (None,"") else None
                except Exception: frp=None
                db.add(FireObservationRecord(
                    fingerprint=fp, source=source, observed_at=observed, lat=lat, lon=lon,
                    frp=frp, confidence=str(row.get("confidence")) if row.get("confidence") is not None else None,
                    payload=row,
                ))
                inserted+=1
            db.commit()
        return inserted
    except Exception:
        return 0

@celery.task(name="vanrakshak.source_health")
def source_health():
    lat, lon = settings.monitor_lat, settings.monitor_lon
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
            out["firms"] = "fallback_mode"
    _run(checks())
    _persist_health(out)
    return {"checked_at": datetime.now(timezone.utc).isoformat(), "sources": out}

@celery.task(name="vanrakshak.fire_context")
def fire_context():
    lat, lon = settings.monitor_lat, settings.monitor_lon
    result: dict = {}
    async def fetch():
        info=await fallback_fire_rows(FIRMSAdapter(),EONETAdapter(),lat,lon,1)
        weather=await OpenMeteoAdapter().current(lat,lon)
        result.update({"fire":info,"weather":weather})
    try:
        _run(fetch())
    except Exception as exc:
        return {"checked_at":datetime.now(timezone.utc).isoformat(),"ok":False,"error":str(exc)}
    rows=result.get("fire",{}).get("rows") or []
    source=result.get("fire",{}).get("source") or "NASA fire intelligence"
    inserted=_persist_fire(rows,source)
    return {
        "checked_at":datetime.now(timezone.utc).isoformat(),
        "ok":True,
        "monitor":{"lat":lat,"lon":lon},
        "source":source,
        "degraded":bool(result.get("fire",{}).get("degraded")),
        "observations":len(rows),
        "inserted":inserted,
    }
