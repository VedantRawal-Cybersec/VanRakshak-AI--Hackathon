from app.adapters.bhuvan import xyz_bbox_wgs84, BhuvanAdapter
from app.adapters.mosdac import MOSDACAdapter
from app.services.evidence import partial_risk
from app.services.model_runtime import status


def test_bhuvan_xyz_bbox_and_wms_url():
    west,south,east,north=xyz_bbox_wgs84(0,0,0)
    assert round(west)==-180 and round(east)==180
    assert south < 0 < north
    u=BhuvanAdapter().tile_request_url(5,23,13,"lulc:BR_LULC50K_1112")
    assert "REQUEST=GetMap" in u and "LAYERS=lulc%3ABR_LULC50K_1112" in u
    assert "SRS=EPSG%3A4326" in u


def test_mosdac_config_matches_official_shape():
    c=MOSDACAdapter.config("3SIMG_L1B_STD","2026-09-01","2026-09-24",50,"70,8,90,28")
    assert c["search_parameters"]["datasetId"]=="3SIMG_L1B_STD"
    assert c["search_parameters"]["count"]=="50"
    assert c["user_credentials"]["username"]==""


def test_partial_risk_excludes_missing_evidence():
    change={"mean_ndvi_change":-0.3,"candidate_area_ha":12,"screening_confidence":0.8}
    sources={"fire":{"ok":False},"human_pressure":{"ok":False}}
    r=partial_risk(change,sources,None)
    assert r["score"] is not None
    assert 0 < r["coverage"] < 1
    assert all(f["factor"]!="Fire activity" for f in r["factors"])


def test_model_status_baseline_is_ready():
    s=status()
    assert s["baseline_remote_change"]["ready"] is True
    assert "opencd" in s
    assert "validated" in s["opencd"]
    assert s["opencd"]["validated"] is False

def test_all_37_feature_capabilities_registered():
    from app.services.feature_status import FEATURE_CAPABILITIES
    assert len(FEATURE_CAPABILITIES)==37
    assert [x["id"] for x in FEATURE_CAPABILITIES]==list(range(1,38))


def test_titiler_satellite_modes_use_indexed_band_math_and_256_tiles():
    from urllib.parse import urlparse, parse_qs
    from app.adapters.earth_search import EarthSearchAdapter
    item={
        "id":"S2-test",
        "properties":{"datetime":"2026-01-01T00:00:00Z","eo:cloud_cover":1.0},
        "links":[{"rel":"self","href":"https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2-test"}],
        "bbox":[75,12,76,13],
    }
    earth=EarthSearchAdapter()
    for mode in ("true_color","false_color","ndvi","ndmi","nbr","ndwi"):
        spec=earth.tile_spec(item,mode)
        q=parse_qs(urlparse(spec["tile_url"]).query)
        assert q.get("tilesize")==["256"]
        assert spec["item_id"]=="S2-test"
    assert parse_qs(urlparse(earth.tile_spec(item,"ndvi")["tile_url"]).query)["expression"]==["(b2-b1)/(b2+b1)"]
    assert parse_qs(urlparse(earth.tile_spec(item,"ndmi")["tile_url"]).query)["expression"]==["(b1-b2)/(b1+b2)"]
    assert parse_qs(urlparse(earth.tile_spec(item,"nbr")["tile_url"]).query)["expression"]==["(b1-b2)/(b1+b2)"]
    assert parse_qs(urlparse(earth.tile_spec(item,"ndwi")["tile_url"]).query)["expression"]==["(b1-b2)/(b1+b2)"]


def test_nasa_power_normalizes_daily_climate_schema(monkeypatch):
    import asyncio
    from app.adapters.nasa_power import NASAPowerAdapter
    async def fake_get_json(self,url,params=None,**kwargs):
        return {"properties":{"parameter":{
            "T2M":{"20260901":24.1,"20260902":-999.0},
            "PRECTOTCORR":{"20260901":5.2,"20260902":0.0},
        }},"header":{"title":"NASA POWER"}}
    monkeypatch.setattr(NASAPowerAdapter,"get_json",fake_get_json)
    out=asyncio.run(NASAPowerAdapter().historical_daily(12.3,75.8,"2026-09-01","2026-09-02"))
    assert out["daily"]["time"]==["2026-09-01","2026-09-02"]
    assert out["daily"]["temperature_2m_mean"]==[24.1,None]
    assert out["daily"]["precipitation_sum"]==[5.2,0.0]
    assert out["source"]=="NASA POWER"
