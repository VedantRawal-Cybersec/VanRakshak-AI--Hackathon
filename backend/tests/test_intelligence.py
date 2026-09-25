from app.models import RiskInputs, CarbonRequest, PatrolRequest, PatrolPoint
from app.services.intelligence import risk_score, cascade, resilience
from app.services.carbon import estimate
from app.services.patrol import optimize
from app.main import _action_plan_from_evidence

def test_risk_monotonicish():
    low=RiskInputs(ndvi_drop=.05,temp_anomaly_c=.2,rainfall_deficit_pct=3,fire_signal=0,fragmentation_change=.05,human_pressure=.1,model_confidence=.7)
    high=RiskInputs(ndvi_drop=.7,temp_anomaly_c=3,rainfall_deficit_pct=60,fire_signal=.8,protected_area=True,fragmentation_change=.7,human_pressure=.8,model_confidence=.9)
    assert risk_score(high)["score"] > risk_score(low)["score"]
    assert risk_score(high)["level"] in {"WARNING","CRITICAL"}

def test_carbon_range():
    out=estimate(CarbonRequest(area_ha=10,biomass_t_per_ha=100,uncertainty_pct=20))
    assert out["co2e_range_t"][0] < out["co2e_t"] < out["co2e_range_t"][1]

def test_patrol_visits_all():
    req=PatrolRequest(start_lat=12.9,start_lon=77.6,points=[PatrolPoint(id="a",lat=13,lon=77.5,priority=90),PatrolPoint(id="b",lat=12.7,lon=77.7,priority=20)])
    out=optimize(req)
    assert {x["id"] for x in out["route"]}=={"a","b"}


def test_action_plan_is_operational_and_measurable():
    inputs=RiskInputs(
        ndvi_drop=.3,temp_anomaly_c=2.0,rainfall_deficit_pct=35,
        fire_signal=.5,protected_area=True,fragmentation_change=.3,
        human_pressure=.4,model_confidence=.8,
    )
    bundle={
        "location":{"lat":12.3375,"lon":75.8069,"place":"Kodagu"},
        "change":{"candidate_area_ha":3.2},
        "sources":{"human_pressure":{"ok":False,"data":None},"fire":{"ok":True,"data":[]}},
        "protected_area":True,
    }
    out=_action_plan_from_evidence(bundle,inputs,12.3375,75.8069)
    assert out["actions"]
    assert out["label"]=="AI_ESTIMATE"
    assert "not guaranteed" in out["expected_outcome"].lower()
    for action in out["actions"]:
        assert action["what"] and action["where"] and action["how"]
        assert action["expected_impact"] and action["success_metric"]
