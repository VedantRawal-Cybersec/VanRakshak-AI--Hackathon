import asyncio
from app.services.source_health import snapshot


class A:
    async def latest_sentinel2(self, *a, **k): return {"features": []}
    async def current(self, *a, **k): return {"current": {}}
    async def point(self, *a, **k): return {"properties": []}
    async def reverse(self, *a, **k): return {"display_name": "Bengaluru"}
    async def latest(self, *a, **k): return {"features": []}
    async def fires(self, *a, **k): return []
    async def india(self, *a, **k): return {"data": []}


def test_source_health_public_providers():
    # Credential-gated providers may legitimately be NOT_CONFIGURED in CI.
    a=A()
    out=asyncio.run(snapshot({"copernicus":a,"earth":a,"weather":a,"soil":a,"geocoder":a,"s1":a,"firms":a,"pp":a}))
    public=[x for x in out["sources"] if x["source"] in {"Copernicus STAC","Earth Search","Open-Meteo","SoilGrids","Nominatim","Sentinel-1 ASF"}]
    assert all(x["ok"] for x in public)
    assert out["healthy_sources"] >= 6
