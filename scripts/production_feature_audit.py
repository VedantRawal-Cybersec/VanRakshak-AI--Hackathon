from __future__ import annotations
import json, os, sys, time
from urllib import request, parse, error

BASE=os.getenv("BASE_URL","https://vanrakshak-api-production-3e28.up.railway.app").rstrip("/")
EXPECTED_SHA=os.getenv("EXPECTED_SHA","").strip()
LAT="12.3375"; LON="75.8069"
BEFORE="2025-11-06"; AFTER="2026-02-04"
START="2025-01-01"; END="2026-09-20"

def call(method,path,payload=None,timeout=240,retries=3):
    url=BASE+path
    body=None
    headers={"Accept":"application/json"}
    if payload is not None:
        body=json.dumps(payload).encode()
        headers["Content-Type"]="application/json"
    last=None
    for i in range(retries):
        try:
            req=request.Request(url,data=body,headers=headers,method=method)
            with request.urlopen(req,timeout=timeout) as r:
                raw=r.read()
                ctype=r.headers.get("content-type","")
                if "json" in ctype:
                    return r.status,json.loads(raw.decode())
                return r.status,raw
        except Exception as exc:
            last=exc
            if i+1<retries: time.sleep(3*(i+1))
    raise RuntimeError(f"{method} {path} failed after {retries} tries: {last}")

def get(path,**kw): return call("GET",path,**kw)
def post(path,payload,**kw): return call("POST",path,payload,**kw)

def ok_source(body):
    return isinstance(body,dict) and body.get("ok") is True and body.get("data") is not None

def nonempty(body):
    return body not in (None,{},[],b"", "")

def q(path,**params):
    return path+"?"+parse.urlencode(params)

print("Waiting for expected Railway revision...",EXPECTED_SHA or "<any>")
for _ in range(60):
    try:
        st,b=get("/api/build-info",timeout=15,retries=1)
        if st==200 and (not EXPECTED_SHA or b.get("git_sha")==EXPECTED_SHA):
            break
    except Exception:
        pass
    time.sleep(10)
else:
    raise SystemExit("Production did not expose expected SHA in time")

live_path=q("/api/intelligence/live",lat=LAT,lon=LON,place="Kodagu",before_date=BEFORE,after_date=AFTER,radius_km=.5,cloud_lt=60)
remote_path=q("/api/analysis/remote-change",lat=LAT,lon=LON,before_date=BEFORE,after_date=AFTER,radius_km=.5,cloud_lt=60)
evidence_path=q("/api/analysis/evidence-chain",lat=LAT,lon=LON,place="Kodagu",before_date=BEFORE,after_date=AFTER,radius_km=.5,cloud_lt=60)
vegetation_path=q("/api/analysis/vegetation-series",lat=LAT,lon=LON,start=START,end=END,max_observations=5,cloud_lt=60,radius_km=.5)
recovery_path=q("/api/analysis/recovery-location",lat=LAT,lon=LON,start=START,end=END,max_observations=5,cloud_lt=60,radius_km=.5)
corr_path=q("/api/analysis/climate-forest-correlation",lat=LAT,lon=LON,start=START,end=END,max_observations=5,cloud_lt=60,radius_km=.5)
predict_path=q("/api/intelligence/predict-location",lat=LAT,lon=LON,start=START,end=END,max_observations=10,cloud_lt=60)
patrol_path=q("/api/patrol/live",lat=LAT,lon=LON,place="Kodagu",before_date=BEFORE,after_date=AFTER,max_points=3)
whatif_path=q("/api/intelligence/what-if-location",lat=LAT,lon=LON,place="Kodagu",before_date=BEFORE,after_date=AFTER,temperature_delta_c=1,rainfall_delta_pct=10,fire_delta=.1,ndvi_delta=.05)
query_live_path=q("/api/query/live",q="show deforestation fire risk and patrol report",lat=LAT,lon=LON,place="Kodagu",before_date=BEFORE,after_date=AFTER)

cache={}
def cached_get(path,timeout=240):
    if path not in cache: cache[path]=get(path,timeout=timeout)
    return cache[path][1]

def test(name,fn):
    t=time.time()
    try:
        detail=fn()
        print(f"PASS | {name} | {time.time()-t:.1f}s | {detail}")
        return True
    except Exception as exc:
        print(f"FAIL | {name} | {time.time()-t:.1f}s | {exc}")
        return False

tests=[]

tests.append(("01 Real Satellite Monitoring",lambda: (
    (lambda b: f"scene={((b.get('data') or {}).get('id') or (b.get('data') or {}).get('features',[{}])[0].get('id'))}" if ok_source(b) else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(q("/api/satellite/latest",lat=LAT,lon=LON,days=365,cloud_lt=80),90))
)))
tests.append(("02 Forest Cover Monitoring",lambda: (
    (lambda b: f"dataset={b.get('dataset') or b.get('source')}" if nonempty(b) else (_ for _ in ()).throw(AssertionError("empty GFW layer")))
    (cached_get(q("/api/map/gfw-layer",dataset="gfw_integrated_alerts"),60))
)))
tests.append(("03 AI Deforestation Detection",lambda: (
    (lambda b: f"candidate_pixels={b.get('candidate_loss_pixels')}" if int(b.get("valid_pixels") or 0)>50 else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(remote_path,220))
)))
tests.append(("04 Before-After Comparison",lambda: (
    (lambda b: f"{b.get('before',{}).get('item_id')} -> {b.get('after',{}).get('item_id')}" if b.get("before",{}).get("tile_url") and b.get("after",{}).get("tile_url") else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(q("/api/map/compare",lat=LAT,lon=LON,before_date=BEFORE,after_date=AFTER,mode="true_color",cloud_lt=60),120))
)))
def satellite_modes_test():
    b=cached_get(q("/api/map/satellite-modes/status",lat=LAT,lon=LON,start_date=BEFORE,end_date=AFTER,cloud_lt=60),300)
    rows=b.get("modes") or []
    if not b.get("ok") or len(rows)!=6 or not all(x.get("ok") for x in rows):
        raise AssertionError(b)
    return "rendered="+",".join(x["mode"] for x in rows)

tests.append(("05 Multi-Spectral Analysis",satellite_modes_test))
tests.append(("06 Multi-Layer Earth Map",lambda: (
    (lambda b: f"groups={len(b.get('groups') or [])}" if len(b.get("groups") or [])>=5 else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get("/api/layers",30))
)))
tests.append(("07 Deep Region Investigation",lambda: (
    (lambda b: f"sources={len(b.get('sources') or {})}" if len(b.get("sources") or {})>=5 else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(q("/api/investigate",lat=LAT,lon=LON,place="Kodagu"),120))
)))
tests.append(("08 Temperature Intelligence",lambda: (
    (lambda b: f"temp={((b.get('data') or {}).get('current') or {}).get('temperature_2m')}" if ok_source(b) else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(q("/api/weather",lat=LAT,lon=LON),60))
)))
tests.append(("09 Weather Intelligence",lambda: (
    (lambda b: f"current_time={((b.get('data') or {}).get('current') or {}).get('time')}" if ok_source(b) else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(q("/api/weather",lat=LAT,lon=LON),60))
)))
tests.append(("10 Drought & Water Stress",lambda: (
    (lambda b: f"rain_deficit={b.get('rainfall_deficit_pct')}" if b.get("rainfall_deficit_pct") is not None else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(q("/api/climate/anomaly",lat=LAT,lon=LON,window_days=30,baseline_years=5),120))
)))
tests.append(("11 Fire & Heat Detection",lambda: (
    (lambda b: f"source={(b.get('provenance') or {}).get('source')} rows={len(b.get('data') or [])}" if b.get("ok") is True else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(q("/api/fire",lat=LAT,lon=LON,days=1),90))
)))
tests.append(("12 Vegetation Health",lambda: (
    (lambda b: f"observations={len(b.get('observations') or [])}" if len(b.get("observations") or [])>=2 else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(vegetation_path,220))
)))
tests.append(("13 Environmental Anomaly Radar",lambda: (
    (lambda b: f"score={(b.get('anomaly_radar') or {}).get('anomaly_score')}" if (b.get("anomaly_radar") or {}).get("anomaly_score") is not None else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(live_path,300))
)))
tests.append(("14 AI Forest Doctor",lambda: (
    (lambda b: f"drivers={len((b.get('forest_doctor') or {}).get('probable_drivers') or [])}" if len((b.get("forest_doctor") or {}).get("probable_drivers") or [])>0 else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(live_path,300))
)))
tests.append(("15 Smart Warning System",lambda: (
    (lambda b: f"risk={(b.get('risk') or {}).get('score')}" if (b.get("risk") or {}).get("score") is not None else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(live_path,300))
)))
def threat_prediction_test():
    b=cached_get(predict_path,300)
    projected=(b.get("projection") or {}).get("projected_values") or b.get("projected_values") or []
    if not projected:
        raise AssertionError(b)
    bt=(b.get("analysis") or {}).get("temporal_backtest") or {}
    if int((b.get("analysis") or {}).get("observation_count") or 0)>=6 and not bt.get("available"):
        raise AssertionError({"message":"real temporal holdout backtest missing despite sufficient Sentinel observations","backtest":bt})
    if bt.get("available"):
        return f"projected={len(projected)} holdout_mae={bt.get('mae')} rmse={bt.get('rmse')}"
    return f"projected={len(projected)} backtest={bt.get('reason','insufficient observations')}"
tests.append(("16 Threat Prediction",threat_prediction_test))
tests.append(("17 Threat Cascade Engine",lambda: (
    (lambda b: f"nodes={len((b.get('cascade') or {}).get('chain') or [])}" if "cascade" in b else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(live_path,300))
)))
tests.append(("18 AI Priority Engine",lambda: (
    (lambda b: f"level={(b.get('risk') or {}).get('level')}" if (b.get("risk") or {}).get("level") else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(live_path,300))
)))
tests.append(("19 Investigation/Patrol Optimizer",lambda: (
    (lambda b: f"stops={len((b.get('ordering') or {}).get('route') or [])}" if len((b.get("ordering") or {}).get("route") or [])>0 else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(patrol_path,300))
)))
tests.append(("20 AI What-If Simulator",lambda: (
    (lambda b: f"baseline_real={bool(b.get('base_from_real_evidence'))}" if b.get("simulation") else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(whatif_path,300))
)))
tests.append(("21 Intervention Engine",lambda: (
    (lambda b: f"recommendations={len((b.get('interventions') or {}).get('recommendations') or [])}" if len((b.get("interventions") or {}).get("recommendations") or [])>0 else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(live_path,300))
)))
tests.append(("22 Recovery Intelligence",lambda: (
    (lambda b: f"status={(b.get('recovery') or {}).get('status')}" if (b.get("recovery") or {}).get("status") else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(recovery_path,240))
)))
tests.append(("23 Recovery Exit Conditions",lambda: (
    (lambda b: f"conditions={len((b.get('recovery') or {}).get('exit_conditions') or {})}" if (b.get("recovery") or {}).get("exit_conditions") else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(recovery_path,240))
)))
tests.append(("24 Forest Resilience Score",lambda: (
    (lambda b: f"score={(b.get('resilience') or {}).get('score')}" if (b.get("resilience") or {}).get("score") is not None else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(live_path,300))
)))
tests.append(("25 Protected Area Intelligence",lambda: (
    (lambda b: f"source={(b.get('provenance') or {}).get('source')}" if b.get("ok") is True and isinstance(b.get("data"),dict) else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(q("/api/protected-area/context",lat=LAT,lon=LON),120))
)))
tests.append(("26 Forest Fragmentation Analysis",lambda: (
    (lambda b: f"patch_delta={((b.get('fragmentation') or {}).get('change') or {}).get('patch_count_delta')}" if (b.get("fragmentation") or {}).get("change") is not None else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(remote_path,220))
)))
def carbon_integrity_test():
    b=cached_get(evidence_path,300)
    local=b.get("carbon")
    ref=b.get("carbon_reference")
    if local:
        if local.get("data_scope")!="SELECTED_LOCATION":
            raise AssertionError({"message":"local carbon lacks selected-location scope","carbon":local})
        return f"local_co2e={local.get('estimated_co2e_t')} class={local.get('estimate_class')}"
    if ref:
        if ref.get("data_scope")!="REGIONAL_REFERENCE_NOT_LOCAL_MEASUREMENT" or ref.get("estimate_class")!="BROAD_REFERENCE_CONTEXT_ONLY":
            raise AssertionError({"message":"broad carbon reference is not safely isolated from local impact","carbon_reference":ref})
        return f"local=unavailable context_only_co2e={ref.get('estimated_co2e_t')}"
    raise AssertionError("Neither location-specific carbon nor explicitly labelled reference context is available")
tests.append(("27 Carbon Loss Calculator",carbon_integrity_test))
tests.append(("28 Climate-Forest Correlation",lambda: (
    (lambda b: f"observations={len(b.get('observations') or [])}" if len(b.get("observations") or [])>=3 else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(corr_path,300))
)))
tests.append(("29 AI Evidence Chain",lambda: (
    (lambda b: f"items={len((b.get('evidence_chain') or {}).get('items') or [])}" if len((b.get("evidence_chain") or {}).get("items") or [])>=3 else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(evidence_path,300))
)))
tests.append(("30 Explainable AI",lambda: (
    (lambda b: f"factors={len((b.get('risk') or {}).get('factors') or [])}" if len((b.get("risk") or {}).get("factors") or [])>0 else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(live_path,300))
)))
tests.append(("31 Natural-Language Earth Query",lambda: (
    (lambda b: f"actions={len((b.get('query') or {}).get('actions') or [])}" if b.get("live_result") else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(query_live_path,300))
)))
tests.append(("32 Automatic Investigation Report",lambda: (
    (lambda b: f"pdf_bytes={len(b)}" if isinstance(b,(bytes,bytearray)) and len(b)>1000 else (_ for _ in ()).throw(AssertionError("PDF too small")))
    (call("GET",q("/api/report/investigation",lat=LAT,lon=LON,place="Kodagu",before_date=BEFORE,after_date=AFTER),timeout=300)[1])
)))
def compare_live_test():
    payload={"regions":[
        {"name":"Kodagu","lat":12.3375,"lon":75.8069,"before_date":"2025-11-06","after_date":"2026-02-04","radius_km":.5},
        {"name":"Agumbe","lat":13.5087,"lon":75.0953,"before_date":"2026-02-14","after_date":"2026-05-15","radius_km":.5},
    ]}
    _,b=post("/api/intelligence/compare-live",payload,timeout=420)
    if len(b.get("regions") or [])<2: raise AssertionError(b)
    return f"regions={len(b['regions'])}"
tests.append(("33 Regional Threat Comparison",compare_live_test))
tests.append(("34 Forest Time Machine",lambda: (
    (lambda b: f"scenes={len(b.get('features') or b.get('scenes') or b.get('items') or [])}" if nonempty(b) else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(q("/api/time-machine",lat=LAT,lon=LON,start=START,end=END,cloud_lt=60,limit=20),120))
)))
tests.append(("35 Live Command Center",lambda: (
    (lambda b: f"checks={b.get('checks')}" if b.get("ok") is True else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get("/api/ready",60))
)))
tests.append(("36 Forest Digital Profile",lambda: (
    (lambda b: f"keys={len(b.keys())}" if isinstance(b,dict) and b.get("location") else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(q("/api/forest-profile",lat=LAT,lon=LON,place="Kodagu"),180))
)))
tests.append(("37 News & Internet Intelligence",lambda: (
    (lambda b: f"source={(b.get('provenance') or {}).get('source')}" if b.get("ok") is True and b.get("data") is not None else (_ for _ in ()).throw(AssertionError(b)))
    (cached_get(q("/api/news",place="Kodagu forest",timespan="1week"),90))
)))

passed=0
for name,fn in tests:
    if test(name,fn): passed+=1

print(f"SUMMARY {passed}/{len(tests)} passed")
if passed!=len(tests):
    sys.exit(1)
