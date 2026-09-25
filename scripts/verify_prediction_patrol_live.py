from __future__ import annotations
import asyncio, json, sys
from app.main import predict_location_ep, remote_change_ep, patrol_road_route, _geojson_centroid
from app.models import PatrolRequest

LAT=12.3375
LON=75.8069
BEFORE="2025-11-06"
AFTER="2026-02-04"

async def main():
    result={"location":{"lat":LAT,"lon":LON},"period":{"before":BEFORE,"after":AFTER},"checks":[]}
    try:
        prediction=await predict_location_ep(LAT,LON,BEFORE,AFTER,8,60)
        p=prediction.get("projection") or {}
        a=p.get("analysis") or {}
        ok=(
            len(prediction.get("source_series") or [])>=3
            and len(p.get("projected_values") or [])==4
            and a.get("confidence_pct") is not None
            and prediction.get("analysis",{}).get("latest_observation")
        )
        result["checks"].append({
            "name":"selected-forest prediction pipeline",
            "ok":bool(ok),
            "observations":len(prediction.get("source_series") or []),
            "latest_observation":prediction.get("analysis",{}).get("latest_observation"),
            "current_risk_index":prediction.get("analysis",{}).get("current_risk_index"),
            "projected_risk_index":prediction.get("analysis",{}).get("projected_risk_index"),
            "model_confidence_pct":a.get("confidence_pct"),
            "trend":a.get("direction"),
        })
    except Exception as exc:
        result["checks"].append({"name":"selected-forest prediction pipeline","ok":False,"error":str(exc)[:1200]})

    try:
        change=await remote_change_ep(LAT,LON,BEFORE,AFTER,.6,.2,.45,60)
        features=((change.get("geojson") or {}).get("features") or [])
        areas=[(f.get("properties") or {}).get("area_ha") for f in features]
        ok=(
            change.get("label")=="DERIVED_METRIC"
            and change.get("screening_confidence") is not None
            and change.get("candidate_area_ha") is not None
            and isinstance(features,list)
        )
        result["checks"].append({
            "name":"patrol change-analysis input",
            "ok":bool(ok),
            "candidate_area_ha":change.get("candidate_area_ha"),
            "candidate_polygons":len(features),
            "component_areas_present":sum(x is not None for x in areas),
            "screening_confidence":change.get("screening_confidence"),
            "before_scene":(change.get("before") or {}).get("id"),
            "after_scene":(change.get("after") or {}).get("id"),
        })

        ranked=sorted(features,key=lambda x:float(((x.get("properties") or {}).get("area_ha") or 0)),reverse=True)
        patrol_points=[]
        for i,feature in enumerate(ranked[:3]):
            center=_geojson_centroid(feature)
            if center is None:
                continue
            plat,plon=center
            area=float(((feature.get("properties") or {}).get("area_ha") or 0))
            patrol_points.append({"id":f"live-hotspot-{i+1}","lat":plat,"lon":plon,"priority":min(100,75+area*5)})
        if patrol_points:
            routed=await patrol_road_route(PatrolRequest(start_lat=LAT,start_lon=LON,points=patrol_points))
            ordering=(routed.get("ordering") or {}).get("route") or []
            road=routed.get("road_route") or {}
            route_ok=len(ordering)==len(patrol_points) and routed.get("status") in {"ROAD_ROUTE_READY","ORDERING_ONLY"}
            result["checks"].append({
                "name":"detected-hotspot patrol execution",
                "ok":bool(route_ok),
                "status":routed.get("status"),
                "stops":len(ordering),
                "ordering_mode":(routed.get("ordering") or {}).get("ordering_mode"),
                "road_distance_km":road.get("distance_km"),
                "duration_min":road.get("duration_min"),
                "routing_error":routed.get("routing_error"),
            })
        else:
            result["checks"].append({"name":"detected-hotspot patrol execution","ok":True,"status":"NO_PATROL_TARGETS","stops":0})
    except Exception as exc:
        result["checks"].append({"name":"patrol change-analysis input","ok":False,"error":str(exc)[:1200]})

    print(json.dumps(result,indent=2))
    return 0 if all(x.get("ok") for x in result["checks"]) else 1

if __name__=="__main__":
    raise SystemExit(asyncio.run(main()))
