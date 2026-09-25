from fastapi.testclient import TestClient
from app.main import app
from app.services.alerts import compose_patrol_alert

client=TestClient(app)


def sample_bundle():
    return {
        "change":{
            "candidate_area_ha":2.4,
            "mean_ndvi_change":-0.12,
            "screening_confidence":0.84,
            "before":{"id":"B","datetime":"2025-11-06T00:00:00Z"},
            "after":{"id":"A","datetime":"2026-02-04T00:00:00Z"},
            "geojson":{
                "type":"FeatureCollection",
                "features":[
                    {"type":"Feature","properties":{"area_ha":1.8},"geometry":{"type":"Polygon","coordinates":[[[75.81,12.34],[75.83,12.34],[75.83,12.36],[75.81,12.36],[75.81,12.34]]]}}
                ],
            },
        },
        "warning":{"level":"HIGH","score":77},
        "forest_doctor":{"probable_drivers":[{"driver":"Road-access pressure","relative_support_pct":63}]},
        "protected_area":True,
        "sources":{"fire":{"ok":True,"data":[],"provenance":{"source":"NASA FIRMS"}}},
        "evidence_chain":{"items":[]},
    }


def test_compose_patrol_alert_has_field_brief_sections():
    out=compose_patrol_alert(sample_bundle(),12.3375,75.8069,"Kodagu Forest Region","VR-TEST")
    assert out["severity"]=="HIGH"
    assert out["top_patrol_target"]["area_ha"]==1.8
    assert "WHERE:" in out["message"]
    assert "WHAT WAS DETECTED:" in out["message"]
    assert "WHEN:" in out["message"]
    assert "HOW IT MAY BE HAPPENING:" in out["message"]
    assert "PATROL FIRST PRIORITY:" in out["message"]
    assert "not proof" in out["message"].lower()


def test_alert_compose_endpoint_uses_evidence(monkeypatch):
    from app import main
    async def fake_evidence(*args,**kwargs):
        return sample_bundle()
    monkeypatch.setattr(main,"evidence_chain_ep",fake_evidence)
    r=client.get("/api/alerts/compose",params={
        "lat":12.3375,"lon":75.8069,"place":"Kodagu Forest Region",
        "before_date":"2025-11-06","after_date":"2026-02-04",
    })
    assert r.status_code==200
    data=r.json()
    assert data["severity"]=="HIGH"
    assert data["change"]["candidate_area_ha"]==2.4
    assert data["top_patrol_target"]["area_ha"]==1.8
    assert data["label"]=="DERIVED_FROM_REAL_EVIDENCE"
    assert "evidence_chain" in data
