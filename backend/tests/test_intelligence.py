from app.models import RiskInputs, CarbonRequest, PatrolRequest, PatrolPoint
from app.services.intelligence import risk_score, cascade, resilience
from app.services.carbon import estimate
from app.services.patrol import optimize

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
