import asyncio
from app.services.source_health import snapshot, _probe


class A:
    async def latest_sentinel2(self, *a, **k): return {"features": []}
    async def current(self, *a, **k): return {"current": {}}
    async def point(self, *a, **k): return {"properties": []}
    async def reverse(self, *a, **k): return {"display_name": "Bengaluru"}
    async def latest(self, *a, **k): return {"features": []}
    async def fires(self, *a, **k): return []
    async def india(self, *a, **k): return {"data": []}
    def health(self): return {"ok": True}


def test_source_health_public_providers():
    # Credential-gated providers may legitimately be NOT_CONFIGURED in CI.
    a=A()
    out=asyncio.run(snapshot({"copernicus":a,"earth":a,"weather":a,"soil":a,"geocoder":a,"s1":a,"firms":a,"pp":a,"ee":a}))
    public=[x for x in out["sources"] if x["source"] in {"Copernicus STAC","Earth Search","Open-Meteo","SoilGrids","Nominatim","Sentinel-1 ASF"}]
    assert all(x["ok"] for x in public)
    assert out["healthy_sources"] >= 6


class Slow:
    async def current(self):
        await asyncio.sleep(.05)
        return {"current": {}}


def test_source_health_probe_timeout_is_bounded():
    out=asyncio.run(_probe("Slow provider",Slow().current(),timeout_s=.01))
    assert out["status"]=="TIMEOUT"
    assert out["ok"] is False
    assert out["latency_ms"] < 100
