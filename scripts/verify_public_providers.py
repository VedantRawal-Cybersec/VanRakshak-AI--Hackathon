from __future__ import annotations
import asyncio, json, sys, math
from datetime import date, timedelta
import httpx
from app.adapters import (
    EarthSearchAdapter, CopernicusAdapter, OpenMeteoAdapter, SoilGridsAdapter, Sentinel1ASFAdapter,
    NominatimAdapter, PhotonAdapter, GIBSAdapter, EONETAdapter, OverpassAdapter, GDELTAdapter, GFWAdapter, NASAPowerAdapter, PlanetaryComputerAdapter,
)

LAT,LON=12.3375,75.8069

def slippy_xy(lat,lon,z=10):
    n=2**z
    x=int((lon+180.0)/360.0*n)
    r=math.radians(max(-85.05112878,min(85.05112878,lat)))
    y=int((1.0-math.asinh(math.tan(r))/math.pi)/2.0*n)
    return max(0,min(n-1,x)),max(0,min(n-1,y))

def mercator_tile_bbox(x,y,z):
    origin=20037508.342789244
    span=2*origin/(2**z)
    minx=-origin+x*span
    maxx=minx+span
    maxy=origin-y*span
    miny=maxy-span
    return f"{minx},{miny},{maxx},{maxy}"

async def satellite_render_smoke(earth):
    data=await earth.latest_sentinel2(LAT,LON,60,80)
    feats=data.get("features") or []
    if not feats: raise RuntimeError("No Sentinel-2 scene for render smoke")
    feats.sort(key=lambda f:(float((f.get("properties") or {}).get("eo:cloud_cover") if (f.get("properties") or {}).get("eo:cloud_cover") is not None else 1000),str((f.get("properties") or {}).get("datetime") or "")))
    item=feats[0]; z=10; x,y=slippy_xy(LAT,LON,z)
    rows=[]
    async with httpx.AsyncClient(timeout=45,follow_redirects=True) as client:
        for mode in ("true_color","false_color","ndvi","ndmi","nbr","ndwi"):
            spec=earth.tile_spec(item,mode)
            url=spec["tile_url"].replace("{z}",str(z)).replace("{x}",str(x)).replace("{y}",str(y))
            r=await client.get(url)
            ctype=(r.headers.get("content-type") or "").lower()
            ok=r.status_code==200 and ctype.startswith("image/") and len(r.content)>100
            rows.append({"mode":mode,"ok":ok,"status":r.status_code,"bytes":len(r.content),"content_type":ctype})
    return {"item_id":item.get("id"),"modes":rows,"ok":all(x["ok"] for x in rows)}

async def gibs_render_smoke(gibs):
    d=(date.today()-timedelta(days=2)).isoformat()
    z=7;x,y=slippy_xy(LAT,LON,z);bbox=mercator_tile_bbox(x,y,z)
    ids=("viirs_snpp_true_color","viirs_snpp_thermal_anomalies","modis_terra_ndvi_8day","modis_terra_lst_day","hls_ndvi_sentinel","hls_moisture_sentinel","hls_nbr_sentinel","hls_ndwi_sentinel")
    rows=[]
    async with httpx.AsyncClient(timeout=35,follow_redirects=True) as client:
        for lid in ids:
            spec=gibs.tile_spec(lid,d)
            url=spec["tile_url"].replace("{bbox-epsg-3857}",bbox).replace("{z}",str(z)).replace("{x}",str(x)).replace("{y}",str(y))
            r=await client.get(url)
            ctype=(r.headers.get("content-type") or "").lower()
            ok=r.status_code==200 and ctype.startswith("image/") and len(r.content)>50
            rows.append({"layer":lid,"ok":ok,"status":r.status_code,"bytes":len(r.content),"content_type":ctype})
    return {"date":d,"layers":rows,"ok":all(x["ok"] for x in rows)}

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
    gibs=GIBSAdapter(); eonet=EONETAdapter(); overpass=OverpassAdapter(); gdelt=GDELTAdapter(); gfw=GFWAdapter(); power=NASAPowerAdapter(); pc=PlanetaryComputerAdapter()
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
        check("NASA POWER",power.health(),lambda x:isinstance(x,dict) and x.get("ok") is True),
        check("Planetary Computer Sentinel-2",pc.latest_sentinel2(LAT,LON,60,80),lambda x:isinstance(x,dict) and "features" in x),
        check("TiTiler Sentinel-2 six-mode rendering",satellite_render_smoke(earth),lambda x:isinstance(x,dict) and x.get("ok") is True),
        check("NASA GIBS environmental raster rendering",gibs_render_smoke(gibs),lambda x:isinstance(x,dict) and x.get("ok") is True),
        check("Overpass protected-area fallback",overpass.containing_protected_areas(LAT,LON),lambda x:isinstance(x,dict) and "elements" in x),
        check("GDELT forest news",gdelt.forest_news("Kodagu Karnataka","1week"),lambda x:isinstance(x,dict)),
        check("GFW RADD radar layer metadata",asyncio.sleep(0, result=gfw.tile_layer("wur_radd_alerts")),lambda x:isinstance(x,dict) and "wur_radd_alerts" in x.get("tile_url","")),
    )
    print(json.dumps({"location":{"lat":LAT,"lon":LON},"checks":checks},indent=2))
    core={"Earth Search Sentinel-2","Open-Meteo","NASA GIBS","NASA EONET","NASA POWER","Planetary Computer Sentinel-2","TiTiler Sentinel-2 six-mode rendering","NASA GIBS environmental raster rendering"}
    failed_core=[x for x in checks if x["source"] in core and not x["ok"]]
    if failed_core:
        print("Core public provider smoke failure:",failed_core,file=sys.stderr)
        return 1
    return 0

if __name__=="__main__":
    raise SystemExit(asyncio.run(main()))
