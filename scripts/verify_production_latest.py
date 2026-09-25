from __future__ import annotations
import json, urllib.request, urllib.parse, sys

# Re-run after disabling Railway config-as-code override for exact runtime bootstrap.\nBASE="https://vanrakshak-api-production-3e28.up.railway.app"

def get(path, timeout=180):
    with urllib.request.urlopen(BASE+path, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8","replace"), dict(r.headers)

def post_json(path, payload, timeout=180):
    data=json.dumps(payload).encode()
    req=urllib.request.Request(BASE+path,data=data,headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8","replace"), dict(r.headers)

checks=[]

status,html,_=get("/")
checks.append(("latest alert HTML", status==200 and 'id="sendAlertBtn"' in html and 'id="alertModal"' in html))

status,js,_=get("/static/app.js")
checks.append(("latest alert JS", status==200 and "openAlertCenter" in js and "attachAlertPatrolRoute" in js))

status,health,_=get("/api/ready")
ready=json.loads(health)
checks.append(("production readiness", status==200 and ready.get("ok") is True and all(ready.get("checks",{}).get(k) is True for k in ["static","database","redis","titiler"])))

q=urllib.parse.urlencode({
    "lat":"12.3375","lon":"75.8069","place":"Kodagu Forest Region",
    "before_date":"2025-11-06","after_date":"2026-02-04",
})
status,body,_=get("/api/alerts/compose?"+q,240)
alert=json.loads(body)
msg=alert.get("message") or ""
checks.append(("live patrol alert", status==200 and alert.get("label")=="DERIVED_FROM_REAL_EVIDENCE" and all(x in msg for x in ["WHERE:","WHAT WAS DETECTED:","WHEN:","HOW IT MAY BE HAPPENING:","PATROL FIRST PRIORITY:"])))

status,body,_=post_json("/api/intelligence/predict",{"values":[20,24,28,31,35],"steps":3,"floor":0,"ceiling":100})
pred=json.loads(body)
checks.append(("live upgraded prediction", status==200 and len(pred.get("projected_values") or [])==3 and (pred.get("analysis") or {}).get("confidence_pct") is not None and ((pred.get("diagnostics") or {}).get("models") or {}).get("theil_sen_robust")))

status,body,_=post_json("/api/patrol/road-route",{
    "start_lat":12.9716,"start_lon":77.5946,
    "points":[
        {"id":"A","lat":12.9750,"lon":77.6000,"priority":85},
        {"id":"B","lat":12.9800,"lon":77.6050,"priority":70}
    ]
},120)
patrol=json.loads(body)
checks.append(("live upgraded patrol", status==200 and patrol.get("status") in {"ROAD_ROUTE_READY","ORDERING_ONLY"} and len((patrol.get("ordering") or {}).get("route") or [])==2))

print(json.dumps({
    "checks":[{"name":name,"ok":bool(ok)} for name,ok in checks],
    "alert_summary":{"severity":alert.get("severity"),"warning_score":alert.get("warning_score"),"candidate_area_ha":(alert.get("change") or {}).get("candidate_area_ha")},
    "prediction_summary":{"direction":(pred.get("analysis") or {}).get("direction"),"confidence_pct":(pred.get("analysis") or {}).get("confidence_pct")},
    "patrol_summary":{"status":patrol.get("status"),"road_distance_km":(patrol.get("road_route") or {}).get("distance_km"),"duration_min":(patrol.get("road_route") or {}).get("duration_min")}
},indent=2))
sys.exit(0 if all(ok for _,ok in checks) else 1)
