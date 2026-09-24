from __future__ import annotations
from app.models import RiskInputs

WEIGHTS = {
    "ndvi_drop": 24,
    "temp_anomaly_c": 10,
    "rainfall_deficit_pct": 12,
    "fire_signal": 16,
    "protected_area": 12,
    "fragmentation_change": 10,
    "human_pressure": 10,
    "model_confidence": 6,
}

def risk_score(x: RiskInputs):
    factors = {
        "Vegetation loss": x.ndvi_drop * WEIGHTS["ndvi_drop"],
        "Temperature anomaly": min(x.temp_anomaly_c / 5, 1) * WEIGHTS["temp_anomaly_c"],
        "Rainfall deficit": x.rainfall_deficit_pct / 100 * WEIGHTS["rainfall_deficit_pct"],
        "Fire signal": x.fire_signal * WEIGHTS["fire_signal"],
        "Protected-area sensitivity": (1 if x.protected_area else 0) * WEIGHTS["protected_area"],
        "Fragmentation": x.fragmentation_change * WEIGHTS["fragmentation_change"],
        "Human pressure": x.human_pressure * WEIGHTS["human_pressure"],
        "Model confidence": x.model_confidence * WEIGHTS["model_confidence"],
    }
    score = round(min(100, sum(factors.values())), 1)
    level = "NORMAL" if score < 25 else "WATCH" if score < 50 else "WARNING" if score < 75 else "CRITICAL"
    ranked = sorted(({"factor":k,"contribution":round(v,1)} for k,v in factors.items()), key=lambda z:z["contribution"], reverse=True)
    return {"score": score, "level": level, "factors": ranked, "method":"transparent weighted evidence model", "label":"AI_ESTIMATE"}

def cascade(x: RiskInputs):
    nodes=[]
    if x.temp_anomaly_c >= 1.5: nodes.append("Heat increase")
    if x.rainfall_deficit_pct >= 20: nodes.append("Drought conditions")
    if x.ndvi_drop >= 0.15: nodes.append("Vegetation stress")
    if x.fire_signal >= 0.35: nodes.append("Fire risk/outbreak")
    if x.ndvi_drop >= 0.3: nodes.append("Canopy loss")
    return {"chain": nodes, "edges": list(zip(nodes,nodes[1:])), "label":"DERIVED_METRIC"}

def intervention(x: RiskInputs):
    rec=[]
    if x.fire_signal > .4: rec.append("Prioritize fire verification and rapid-response readiness")
    if x.rainfall_deficit_pct > 30: rec.append("Increase drought/water-stress monitoring cadence")
    if x.human_pressure > .5: rec.append("Prioritize field verification near access routes and settlements")
    if x.protected_area: rec.append("Escalate to protected-area management workflow")
    if x.fragmentation_change > .25: rec.append("Protect corridor/core-forest connectivity around the disturbance")
    if not rec: rec.append("Continue routine monitoring and validate on the next suitable observation")
    return rec

def resilience(x: RiskInputs):
    penalty = (x.ndvi_drop*30 + min(x.temp_anomaly_c/5,1)*15 + x.rainfall_deficit_pct/100*20 + x.fire_signal*15 + x.fragmentation_change*10 + x.human_pressure*10)
    score = round(max(0, 100-penalty),1)
    return {"score":score,"band":"LOW" if score<40 else "MODERATE" if score<70 else "HIGH","label":"AI_ESTIMATE"}

from app.models import ForestDoctorInputs, RecoveryInputs, CorrelationInputs, RegionComparisonRequest
import numpy as np

def forest_doctor(x: ForestDoctorInputs):
    scores={"Agricultural expansion":0.0,"Logging / clearing":0.0,"Fire-related disturbance":0.0,"Mining / infrastructure":0.0,"Drought / natural stress":0.0}
    scores["Agricultural expansion"] += 60*x.landcover_to_crop + 10*x.ndvi_drop
    scores["Logging / clearing"] += 30*x.ndvi_drop + 25*x.radar_change
    scores["Fire-related disturbance"] += 70*x.fire_signal + 10*x.ndvi_drop
    scores["Drought / natural stress"] += 60*x.drought_severity + 10*x.ndvi_drop
    if x.road_proximity_km is not None: scores["Logging / clearing"] += max(0,15*(1-min(x.road_proximity_km/5,1)))
    if x.settlement_proximity_km is not None: scores["Agricultural expansion"] += max(0,10*(1-min(x.settlement_proximity_km/5,1)))
    if x.mining_or_quarry_nearby: scores["Mining / infrastructure"] += 65
    total=sum(scores.values()) or 1
    ranked=sorted(({"driver":k,"relative_support_pct":round(v/total*100,1)} for k,v in scores.items()),key=lambda z:z["relative_support_pct"],reverse=True)
    return {"probable_drivers":ranked,"label":"AI_ESTIMATE","warning":"Probable drivers are hypotheses from evidence fusion, not proof of causation."}

def recovery(x: RecoveryInputs):
    ndvi_ratio = 1.0 if x.ndvi_baseline <= 0 else max(0,min(1,x.ndvi_current/x.ndvi_baseline))
    cover_ratio = 1.0 if x.forest_cover_baseline <= 0 else max(0,min(1,x.forest_cover_current/x.forest_cover_baseline))
    moisture = x.soil_moisture_percentile/100
    fire_penalty=.2 if x.recent_fire else 0
    score=max(0,min(100,(0.45*ndvi_ratio+0.4*cover_ratio+0.15*moisture-fire_penalty)*100))
    status="DETERIORATING" if score<40 else "STABILIZING" if score<65 else "RECOVERING"
    exits={"Watch": ["NDVI >= 70% of baseline","forest cover >= 75% of baseline","no recent active-fire signal"],"Normal":["NDVI >= 90% of baseline","forest cover >= 90% of baseline","soil moisture >= 40th percentile","no recent active-fire signal"]}
    return {"recovery_score":round(score,1),"status":status,"exit_conditions":exits,"label":"AI_ESTIMATE"}

def correlations(x: CorrelationInputs):
    series={"temperature":x.temperature,"rainfall":x.rainfall,"ndvi":x.ndvi,"fire":x.fire,"forest_loss":x.forest_loss}
    lens={len(v) for v in series.values()}
    if len(lens)!=1 or next(iter(lens),0)<3: raise ValueError("All series must have equal length >= 3")
    keys=list(series); out={}
    for i,a in enumerate(keys):
        for b in keys[i+1:]:
            aa=np.array(series[a],dtype=float); bb=np.array(series[b],dtype=float)
            if np.std(aa)==0 or np.std(bb)==0: corr=None
            else: corr=round(float(np.corrcoef(aa,bb)[0,1]),3)
            out[f"{a}__{b}"]=corr
    return {"pearson":out,"sample_count":next(iter(lens)),"label":"DERIVED_METRIC","warning":"Correlation does not establish causation."}

def compare_regions(req: RegionComparisonRequest):
    rows=[]
    for r in req.regions:
        index = r.risk*.55 + min(r.forest_loss_ha/100,1)*20 + min(r.fire_count/20,1)*10 + r.ndvi_drop*10 + (5 if r.protected_area else 0)
        rows.append({**r.model_dump(),"priority_index":round(min(100,index),1)})
    return {"regions":sorted(rows,key=lambda z:z["priority_index"],reverse=True),"label":"DERIVED_METRIC"}

def anomaly_radar(signals: dict[str,float]):
    # Inputs are expected to be normalized anomaly magnitudes 0..1 from source-specific baselines.
    vals={k:max(0,min(1,float(v))) for k,v in signals.items()}
    score=round(100*np.mean(list(vals.values())),1) if vals else 0
    severe=[k for k,v in vals.items() if v>=.7]
    return {"anomaly_score":score,"severe_signals":severe,"signals":vals,"level":"HIGH" if score>=65 else "MODERATE" if score>=35 else "LOW","label":"DERIVED_METRIC"}
