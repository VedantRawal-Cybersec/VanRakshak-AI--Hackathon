from __future__ import annotations
from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings

class OSRMAdapter(BaseAdapter):
    name="osrm"
    source_url="https://router.project-osrm.org"

    @staticmethod
    def _coords(points):
        return ";".join(f"{lon},{lat}" for lat,lon in points)

    async def table(self,points:list[tuple[float,float]]):
        if len(points)<2: raise AdapterError("At least two points are required")
        url=f"{settings.osrm_url.rstrip('/')}/table/v1/driving/{self._coords(points)}"
        data=await self.get_json(url,params={"annotations":"duration,distance","radiuses":";".join(["5000"]*len(points))})
        if data.get("code") not in {None,"Ok"}: raise AdapterError(data.get("message") or "OSRM table request failed")
        if not data.get("durations"): raise AdapterError("OSRM returned no travel-time matrix")
        return {"durations":data["durations"],"distances":data.get("distances"),"source":"OSRM/OpenStreetMap"}

    @staticmethod
    def _instruction(step):
        man=step.get("maneuver") or {}; typ=str(man.get("type") or "continue").replace("_"," "); mod=str(man.get("modifier") or "").replace("_"," "); name=str(step.get("name") or "").strip()
        text=f"{typ.title()}{(' '+mod) if mod else ''}"
        return text+(f" on {name}" if name else "")

    async def route(self,points:list[tuple[float,float]]):
        if len(points)<2: raise AdapterError("At least two points are required")
        url=f"{settings.osrm_url.rstrip('/')}/route/v1/driving/{self._coords(points)}"
        data=await self.get_json(url,params={"overview":"full","geometries":"geojson","steps":"true","annotations":"false","radiuses":";".join(["5000"]*len(points))})
        routes=data.get("routes") or []
        if not routes: raise AdapterError(data.get("message") or "OSRM returned no route")
        r=routes[0]; legs=[]
        for i,leg in enumerate(r.get("legs") or []):
            steps=[{"instruction":self._instruction(s),"distance_m":round(float(s.get("distance") or 0),1),"duration_min":round(float(s.get("duration") or 0)/60.0,1)} for s in leg.get("steps") or [] if float(s.get("distance") or 0)>=2]
            legs.append({"leg":i+1,"distance_km":round(float(leg.get("distance") or 0)/1000.0,2),"duration_min":round(float(leg.get("duration") or 0)/60.0,1),"steps":steps})
        return {"distance_km":round(float(r.get("distance") or 0)/1000.0,2),"duration_min":round(float(r.get("duration") or 0)/60.0,1),"geometry":r.get("geometry"),"legs":legs,"source":"OSRM/OpenStreetMap"}
