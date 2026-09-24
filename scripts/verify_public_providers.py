from __future__ import annotations
import asyncio, json, sys
from app.adapters import (
    EarthSearchAdapter, CopernicusAdapter, OpenMeteoAdapter, SoilGridsAdapter, Sentinel1ASFAdapter,
    NominatimAdapter, PhotonAdapter, GIBSAdapter, EONETAdapter, OverpassAdapter, GDELTAdapter, GFWAdapter,
)

LAT,LON=12.3375,75.8069

async def check(name, coro, validator=lambda x: x is not None):
    try:
        data=await coro
        ok=bool(validator(data))
        return {"source":name,"ok":ok,"detail":None if ok else "validator returned false"}
    except Exception as exc:
        return {"source":name,"ok":False,"detail":str(exc)[:300]}

async def main():
    earth=EarthSearchAdapter(); cop=CopernicusAdapter(); weather=OpenMeteoAdapter(); soil=SoilGridsAdapter()
    s1=Sentinel1ASFAdapter(); nom=NominatimAdapter(); photon=PhotonAdapter()
    gibs=GIBSAdapter(); eonet=EONETAdapter(); overpass=OverpassAdapter(); gdelt=GDELTAdapter(); gfw=GFWAdapter()
    checks=await asyncio.gather(
        check("Earth Search Sentinel-2",earth.latest_sentinel2(LAT,LON,60,80),lambda x:isinstance(x,dict) and "features" in x),
        check("Copernicus STAC",cop.latest_sentinel2(LAT,LON,60,80),lambda x:isinstance(x,dict) and "features" in x),
        check("Open-Meteo",weather.current(LAT,LON),lambda x:isinstance(x,dict) and "current" in x),
        check("SoilGrids",soil.point(LAT,LON),lambda x:isinstance(x,dict)),
        check("ASF Sentinel-1",s1.latest(LAT,LON,60,3),lambda x:isinstance(x,dict)),
        check("Nominatim",nom.reverse(LAT,LON),lambda x:isinstance(x,dict) and bool(x)),
        check("Photon",photon.search("Kodagu Karnataka",1),lambda x:isinstance(x,list)),
        check("NASA GIBS",gibs.health(),lambda x:isinstance(x,dict) and x.get("ok") is True),
        check("NASA EONET",eonet.events(LAT,LON,30,3,5),lambda x:isinstance(x,dict) and "events" in x),
        check("Overpass protected-area fallback",overpass.containing_protected_areas(LAT,LON),lambda x:isinstance(x,dict) and "elements" in x),
        check("GDELT forest news",gdelt.forest_news("Kodagu Karnataka","1week"),lambda x:isinstance(x,dict)),
        check("GFW RADD radar layer metadata",asyncio.sleep(0, result=gfw.tile_layer("wur_radd_alerts")),lambda x:isinstance(x,dict) and "wur_radd_alerts" in x.get("tile_url","")),
    )
    print(json.dumps({"location":{"lat":LAT,"lon":LON},"checks":checks},indent=2))
    core={"Earth Search Sentinel-2","Open-Meteo","NASA GIBS","NASA EONET"}
    failed_core=[x for x in checks if x["source"] in core and not x["ok"]]
    if failed_core:
        print("Core public provider smoke failure:",failed_core,file=sys.stderr)
        return 1
    return 0

if __name__=="__main__":
    raise SystemExit(asyncio.run(main()))
