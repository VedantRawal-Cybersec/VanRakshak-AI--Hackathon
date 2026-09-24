import asyncio
from app.adapters.gibs import GIBSAdapter
from app.adapters.eonet import EONETAdapter
from app.adapters.photon import PhotonAdapter
from app.services.fallbacks import geocode_search, reverse_geocode, protected_context, provider_strategy


def test_gibs_maplibre_tile_spec_is_keyless_and_web_mercator():
    spec=GIBSAdapter().tile_spec("modis_terra_true_color","2026-09-20")
    assert spec["auth_required"] is False
    assert "/wmts/epsg3857/best/" in spec["tile_url"]
    assert "MODIS_Terra_CorrectedReflectance_TrueColor" in spec["tile_url"]
    assert "{z}/{y}/{x}.jpg" in spec["tile_url"]


def test_photon_normalizes_geojson_to_nominatim_shape():
    rows=PhotonAdapter._normalize({"features":[{
        "geometry":{"type":"Point","coordinates":[77.59,12.97]},
        "properties":{"name":"Bengaluru","state":"Karnataka","country":"India"}
    }]})
    assert rows[0]["lat"]=="12.97"
    assert rows[0]["lon"]=="77.59"
    assert rows[0]["geojson"]["type"]=="Point"


class BadNominatim:
    async def search(self,*a,**k): raise RuntimeError("down")
    async def reverse(self,*a,**k): raise RuntimeError("down")

class GoodPhoton:
    async def search(self,*a,**k): return [{"lat":"12","lon":"77","display_name":"Fallback","geojson":{"type":"Point","coordinates":[77,12]}}]
    async def reverse(self,*a,**k): return {"lat":"12","lon":"77","display_name":"Fallback"}

def test_geocoding_uses_photon_when_nominatim_fails():
    out=asyncio.run(geocode_search(BadNominatim(),GoodPhoton(),"Bandipur",5))
    assert out["degraded"] is True
    assert out["source"].startswith("Photon")
    rev=asyncio.run(reverse_geocode(BadNominatim(),GoodPhoton(),12,77))
    assert rev["data"]["display_name"]=="Fallback"


class FakeOverpass:
    async def containing_protected_areas(self,*a,**k):
        return {"elements":[{"id":1,"type":"area","tags":{"name":"Test Reserve"},"center":{"lat":12.0,"lon":77.0}}]}

class FakeEE:
    def sample(self,*a,**k): raise RuntimeError("not configured")

def test_protected_context_has_osm_fallback():
    out=asyncio.run(protected_context(FakeOverpass(),FakeEE(),12,77))
    assert out["inside"] is True
    assert out["degraded"] is True
    assert out["areas"][0]["tags"]["name"]=="Test Reserve"


class FakeEONET(EONETAdapter):
    async def events(self,*a,**k):
        return {"events":[{
            "id":"E1","title":"Wildfire","categories":[{"title":"Wildfires"}],
            "geometry":[{"type":"Point","coordinates":[77.5,12.5],"date":"2026-09-24T10:00:00Z"}]
        }]}

def test_eonet_wildfire_context_normalizes_points():
    rows=asyncio.run(FakeEONET().wildfire_points(12.5,77.5))
    assert rows[0]["latitude"]==12.5
    assert rows[0]["event_id"]=="E1"
    assert rows[0]["_firms_source"]=="NASA_EONET_WILDFIRE_CONTEXT"


def test_provider_strategy_keeps_37_feature_stack_resilient():
    s=provider_strategy()
    assert s["fire"]["credential_free_fallback"] is True
    assert s["protected_areas"]["credential_free_fallback"] is True
    assert s["satellite"]["credential_free"] is True


def test_overpass_uses_multiple_global_fallback_instances():
    from app.adapters.overpass import OverpassAdapter
    endpoints=OverpassAdapter.endpoints()
    assert len(endpoints) >= 3
    assert endpoints[0]
    assert "https://overpass.private.coffee/api/interpreter" in endpoints
    assert "https://maps.mail.ru/osm/tools/overpass/api/interpreter" in endpoints
