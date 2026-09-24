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
