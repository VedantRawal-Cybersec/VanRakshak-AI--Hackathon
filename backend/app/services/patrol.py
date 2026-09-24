from __future__ import annotations
from math import radians, sin, cos, asin, sqrt
from app.models import PatrolRequest

def haversine(a,b,c,d):
    lat1,lon1,lat2,lon2=map(radians,[a,b,c,d]); x=sin((lat2-lat1)/2)**2+cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 6371*2*asin(sqrt(x))

def optimize(req: PatrolRequest):
    remaining=req.points[:]; lat,lon=req.start_lat,req.start_lon; route=[]; total=0.0
    while remaining:
        nxt=min(remaining,key=lambda p: haversine(lat,lon,p.lat,p.lon)/(1+p.priority/100))
        d=haversine(lat,lon,nxt.lat,nxt.lon); total+=d
        route.append({"id":nxt.id,"lat":nxt.lat,"lon":nxt.lon,"priority":nxt.priority,"distance_from_previous_km":round(d,2)})
        lat,lon=nxt.lat,nxt.lon; remaining.remove(nxt)
    return {"route":route,"estimated_straight_line_km":round(total,2),"note":"Priority-aware nearest-neighbour ordering. Integrate GraphHopper/OR-Tools for road-network production routing."}
