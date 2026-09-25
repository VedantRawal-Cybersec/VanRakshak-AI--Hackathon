from __future__ import annotations
from math import radians, sin, cos, asin, sqrt
from app.models import PatrolRequest

def haversine(a,b,c,d):
    lat1,lon1,lat2,lon2=map(radians,[a,b,c,d]); x=sin((lat2-lat1)/2)**2+cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 6371*2*asin(sqrt(x))

def _matrix_value(matrix,row,col):
    try:
        value=matrix[row][col]
        return None if value is None else float(value)
    except Exception:
        return None

def optimize(req: PatrolRequest, duration_matrix=None, distance_matrix=None):
    if not req.points: raise ValueError("At least one patrol stop is required")
    remaining=[(i+1,p) for i,p in enumerate(req.points)]
    current_index=0; current_lat,current_lon=req.start_lat,req.start_lon
    route=[]; total_straight=0.0; estimated_road_km=0.0; estimated_road_min=0.0
    matrix_used=bool(duration_matrix)
    while remaining:
        ranked=[]
        for matrix_index,p in remaining:
            straight=haversine(current_lat,current_lon,p.lat,p.lon)
            dur_s=_matrix_value(duration_matrix,current_index,matrix_index) if matrix_used else None
            dist_m=_matrix_value(distance_matrix,current_index,matrix_index) if distance_matrix else None
            travel_min=dur_s/60.0 if dur_s is not None and dur_s>=0 else max(1.0,straight/25.0*60.0)
            priority_factor=.45+1.55*(float(p.priority)/100.0)
            ranked.append((travel_min/priority_factor,-float(p.priority),travel_min,straight,dist_m,matrix_index,p))
        ranked.sort(key=lambda x:(x[0],x[1],x[2]))
        score,_,travel_min,straight,dist_m,matrix_index,nxt=ranked[0]
        total_straight+=straight
        if dist_m is not None: estimated_road_km+=dist_m/1000.0
        if matrix_used: estimated_road_min+=travel_min
        band="CRITICAL" if nxt.priority>=85 else "HIGH" if nxt.priority>=65 else "MEDIUM" if nxt.priority>=40 else "LOW"
        route.append({"order":len(route)+1,"input_index":matrix_index-1,"id":nxt.id,"lat":nxt.lat,"lon":nxt.lon,"priority":round(float(nxt.priority),1),"priority_band":band,"distance_from_previous_km":round(straight,2),"estimated_road_leg_km":round(dist_m/1000.0,2) if dist_m is not None else None,"estimated_road_leg_min":round(travel_min,1) if matrix_used else None,"selection_score":round(score,3),"why_selected":f"{band.title()} priority ({float(nxt.priority):.0f}/100) balanced against {'road travel time' if matrix_used else 'straight-line distance'} from the previous stop."})
        current_lat,current_lon=nxt.lat,nxt.lon; current_index=matrix_index
        remaining=[x for x in remaining if x[0]!=matrix_index]
    return {"route":route,"stop_count":len(route),"estimated_straight_line_km":round(total_straight,2),"matrix_estimated_road_km":round(estimated_road_km,2) if distance_matrix else None,"matrix_estimated_duration_min":round(estimated_road_min,1) if matrix_used else None,"ordering_mode":"ROAD_TIME_PRIORITY" if matrix_used else "DISTANCE_PRIORITY_FALLBACK","method":"priority-weighted greedy ordering using OSRM road travel time when available; haversine distance fallback otherwise","note":"Priority affects visit order, while travel cost prevents extreme zig-zagging. Final road geometry is requested separately from OSRM."}
