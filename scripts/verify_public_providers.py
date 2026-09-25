from __future__ import annotations
import asyncio, json, sys, math
from datetime import date, timedelta
import httpx
from app.adapters import (
    EarthSearchAdapter, CopernicusAdapter, OpenMeteoAdapter, SoilGridsAdapter, Sentinel1ASFAdapter,
    NominatimAdapter, PhotonAdapter, GIBSAdapter, EONETAdapter, OverpassAdapter, GDELTAdapter, GFWAdapter, NASAPowerAdapter, PlanetaryComputerAdapter, GoogleNewsRSSAdapter, METNorwayAdapter,
    USGSLandsatAdapter, GCPLandsatAdapter, OSRMAdapter,
)
from app.services.historical_landsat_tiles import render_png as render_historical_landsat_png, parse_mtl

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

async def filtered_satellite_smoke(earth):
    from datetime import datetime, timezone
    start=datetime(2025,11,1,tzinfo=timezone.utc)
    end=datetime(2025,11,16,tzinfo=timezone.utc)
    data=await earth.search(LAT,LON,start,end,"sentinel-2-l2a",60,30)
    feats=data.get("features") or []
    if not feats:
        raise RuntimeError("No Sentinel-2 scene returned for fixed date/cloud filter")
    valid=[]
    for item in feats:
        p=item.get("properties") or {}
        dt=str(p.get("datetime") or "")
        cloud=p.get("eo:cloud_cover")
        try:
            when=datetime.fromisoformat(dt.replace("Z","+00:00"))
        except Exception:
            continue
        if start <= when < end and (cloud is None or float(cloud)<60):
            valid.append(item)
    if not valid:
        raise RuntimeError("Earth Search returned scenes outside the requested date/cloud filters")
    valid.sort(key=lambda item:str((item.get("properties") or {}).get("datetime") or ""),reverse=True)
    item=valid[0]
    z=10;x,y=slippy_xy(LAT,LON,z)
    spec=earth.tile_spec(item,"ndvi")
    url=spec["tile_url"].replace("{z}",str(z)).replace("{x}",str(x)).replace("{y}",str(y))
    async with httpx.AsyncClient(timeout=45,follow_redirects=True) as client:
        r=await client.get(url)
    ctype=(r.headers.get("content-type") or "").lower()
    ok=r.status_code==200 and ctype.startswith("image/") and len(r.content)>100
    if not ok:
        raise RuntimeError(f"Filtered NDVI tile failed: status={r.status_code} type={ctype} bytes={len(r.content)}")
    p=item.get("properties") or {}
    return {"ok":True,"item_id":item.get("id"),"datetime":p.get("datetime"),"cloud_cover":p.get("eo:cloud_cover"),"mode":"ndvi","bytes":len(r.content)}

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

async def planetary_render_smoke(pc):
    data=await pc.latest_sentinel2(LAT,LON,60,80)
    feats=data.get("features") or []
    if not feats: raise RuntimeError("No Planetary Computer Sentinel-2 scene for render smoke")
    feats.sort(key=lambda f:(float((f.get("properties") or {}).get("eo:cloud_cover") if (f.get("properties") or {}).get("eo:cloud_cover") is not None else 1000),str((f.get("properties") or {}).get("datetime") or "")))
    item=feats[0]; z=10; x,y=slippy_xy(LAT,LON,z)
    rows=[]
    async with httpx.AsyncClient(timeout=45,follow_redirects=True) as client:
        for mode in ("true_color","false_color","ndvi","ndmi","nbr","ndwi"):
            spec=await pc.tile_spec(item,mode)
            url=spec["tile_url"].replace("{z}",str(z)).replace("{x}",str(x)).replace("{y}",str(y))
            r=await client.get(url)
            ctype=(r.headers.get("content-type") or "").lower()
            ok=r.status_code==200 and ctype.startswith("image/") and len(r.content)>100
            rows.append({"mode":mode,"ok":ok,"status":r.status_code,"bytes":len(r.content),"content_type":ctype})
    return {"item_id":item.get("id"),"modes":rows,"ok":all(x["ok"] for x in rows)}

async def historical_landsat_smoke(usgs,gcp):
    from datetime import datetime, timezone
    target=datetime(1987,6,1,tzinfo=timezone.utc)
    item=await usgs.closest_scene(LAT,LON,target,90,100,550)
    catalog="USGS Landsat STAC"
    if not item:
        products=await gcp._discover_products(LAT,LON,target,550)
        item=await gcp.closest_scene(LAT,LON,target,90,100,550)
        catalog="Google Cloud public Landsat Collection 1"
    else:
        products=[]
    if not item:
        metadata_debug=[]
        for _,candidate in products[:3]:
            try:
                raw=await gcp.metadata(candidate)
                metadata_debug.append({
                    "product":candidate,
                    "summary":gcp._metadata_summary(raw),
                    "has_reflectance":"REFLECTANCE_MULT_BAND_" in raw,
                    "bytes":len(raw),
                })
            except Exception as exc:
                metadata_debug.append({"product":candidate,"error":str(exc)})
        raise RuntimeError(
            "No verified Landsat observation within 550 days of 1987-06-01; "
            f"WRS candidates={gcp.wrs2_candidates(LAT,LON)} archive_products={products[:5]} "
            f"metadata={metadata_debug}"
        )
    product=await gcp.resolve_item(item)
    if not product:
        raise RuntimeError(f"Google public Landsat mirror has no Collection-1 raster matching {item.get('id')}")
    metadata=await gcp.metadata(product)
    meta=parse_mtl(metadata)
    calibration_keys=sorted(k for k in meta if k.startswith("REFLECTANCE_") or k.startswith("RADIANCE_"))
    if not calibration_keys:
        raise RuntimeError("Historical Landsat MTL exposes no radiometric calibration coefficients")
    z=9; x,y=slippy_xy(LAT,LON,z)
    rows=[]
    urls=gcp.asset_urls(product)
    for mode in ("true_color","ndvi"):
        png=await asyncio.to_thread(render_historical_landsat_png,urls,metadata,mode,z,x,y)
        ok=png.startswith(b"\\x89PNG\\r\\n\\x1a\\n") and len(png)>100
        rows.append({"mode":mode,"ok":ok,"bytes":len(png)})
    if not all(row["ok"] for row in rows):
        raise RuntimeError("Historical Landsat raster renderer did not return valid PNGs")
    props=item.get("properties") or {}
    archive=item.get("_vanrakshak_archive") or {}
    return {
        "ok":True,
        "item_id":item.get("id"),
        "product_id":product,
        "catalog":catalog,
        "datetime":props.get("datetime"),
        "date_offset_days":archive.get("date_offset_days"),
        "calibration_keys":calibration_keys[:8],
        "renders":rows,
    }


async def gibs_render_smoke(gibs):
    d=(date.today()-timedelta(days=2)).isoformat()
    z=7;x,y=slippy_xy(LAT,LON,z);bbox=mercator_tile_bbox(x,y,z)
    ids=("viirs_snpp_true_color","viirs_snpp_thermal_anomalies","modis_terra_ndvi_8day","modis_terra_lst_day","imerg_precipitation_rate","opera_dist_alert_hls","opera_surface_water_hls","smap_soil_moisture")
    rows=[]
    async with httpx.AsyncClient(timeout=35,follow_redirects=True) as client:
        for lid in ids:
            spec=gibs.tile_spec(lid,d)
            url=spec["tile_url"].replace("{bbox-epsg-3857}",bbox).replace("{z}",str(z)).replace("{x}",str(x)).replace("{y}",str(y))
            r=await client.get(url)
            ctype=(r.headers.get("content-type") or "").lower()
            ok=r.status_code==200 and ctype.startswith("image/") and len(r.content)>50
            rows.append({"layer":lid,"ok":ok,"status":r.status_code,"bytes":len(r.content),"content_type":ctype})
    result={"date":d,"layers":rows,"ok":all(x["ok"] for x in rows)}
    if not result["ok"]:
        failed=[x for x in rows if not x["ok"]]
        raise RuntimeError("NASA GIBS render failures: "+json.dumps(failed,sort_keys=True))
    return result

async def osrm_routing_smoke(osrm):
    # Stable urban road points verify the public engine itself; forest route
    # completeness remains location-dependent and is surfaced in the UI.
    points=[(12.9716,77.5946),(12.9750,77.6000),(12.9800,77.6050)]
    table=await osrm.table(points)
    durations=table.get("durations") or []
    if len(durations)!=len(points) or any(len(row)!=len(points) for row in durations):
        raise RuntimeError("OSRM travel-time matrix shape is invalid")
    route=await osrm.route(points)
    geom=route.get("geometry") or {}
    if route.get("distance_km",0)<=0 or route.get("duration_min",0)<=0 or geom.get("type")!="LineString":
        raise RuntimeError("OSRM route did not return positive distance/duration and LineString geometry")
    legs=route.get("legs") or []
    if len(legs)<2:
        raise RuntimeError("OSRM route did not expose expected route legs")
    return {"ok":True,"distance_km":route.get("distance_km"),"duration_min":route.get("duration_min"),"matrix_size":len(durations),"legs":len(legs),"source":route.get("source")}


async def check(name, coro, validator=lambda x: x is not None):
    try:
        data=await coro
        ok=bool(validator(data))
        return {"source":name,"ok":ok,"detail":None if ok else "validator returned false"}
    except Exception as exc:
        return {"source":name,"ok":False,"detail":str(exc)[:1800]}

async def main():
    earth=EarthSearchAdapter(); cop=CopernicusAdapter(); weather=OpenMeteoAdapter(); soil=SoilGridsAdapter()
    s1=Sentinel1ASFAdapter(); nom=NominatimAdapter(); photon=PhotonAdapter()
    gibs=GIBSAdapter(); eonet=EONETAdapter(); overpass=OverpassAdapter(); gdelt=GDELTAdapter(); gfw=GFWAdapter(); power=NASAPowerAdapter(); pc=PlanetaryComputerAdapter(); gnews=GoogleNewsRSSAdapter(); metno=METNorwayAdapter(); usgs=USGSLandsatAdapter(); gcp=GCPLandsatAdapter(); osrm=OSRMAdapter()
    checks=await asyncio.gather(
        check("Earth Search Sentinel-2",earth.latest_sentinel2(LAT,LON,60,80),lambda x:isinstance(x,dict) and "features" in x),
        check("Copernicus STAC",cop.latest_sentinel2(LAT,LON,60,80),lambda x:isinstance(x,dict) and "features" in x),
        check("Open-Meteo",weather.current(LAT,LON),lambda x:isinstance(x,dict) and "current" in x),
        check("MET Norway",metno.current(LAT,LON),lambda x:isinstance(x,dict) and "current" in x),
        check("SoilGrids",soil.point(LAT,LON),lambda x:isinstance(x,dict)),
        check("ASF Sentinel-1",s1.latest(LAT,LON,60,3),lambda x:isinstance(x,dict)),
        check("Nominatim",nom.reverse(LAT,LON),lambda x:isinstance(x,dict) and bool(x)),
        check("Photon",photon.search("Kodagu Karnataka",1),lambda x:isinstance(x,list)),
        check("NASA GIBS",gibs.health(),lambda x:isinstance(x,dict) and x.get("ok") is True),
        check("NASA EONET",eonet.events(LAT,LON,30,3,5),lambda x:isinstance(x,dict) and "events" in x),
        check("NASA POWER",power.health(),lambda x:isinstance(x,dict) and x.get("ok") is True),
        check("Planetary Computer Sentinel-2",pc.latest_sentinel2(LAT,LON,60,80),lambda x:isinstance(x,dict) and "features" in x),
        check("TiTiler Sentinel-2 six-mode rendering",satellite_render_smoke(earth),lambda x:isinstance(x,dict) and x.get("ok") is True),
        check("Sentinel-2 filtered date/cloud rendering",filtered_satellite_smoke(earth),lambda x:isinstance(x,dict) and x.get("ok") is True),
        check("Planetary Computer six-mode rendering",planetary_render_smoke(pc),lambda x:isinstance(x,dict) and x.get("ok") is True),
        check("Historical Landsat 1987 archive rendering",historical_landsat_smoke(usgs,gcp),lambda x:isinstance(x,dict) and x.get("ok") is True),
        check("OSRM patrol matrix + route rendering",osrm_routing_smoke(osrm),lambda x:isinstance(x,dict) and x.get("ok") is True),
        check("NASA GIBS environmental raster rendering",gibs_render_smoke(gibs),lambda x:isinstance(x,dict) and x.get("ok") is True),
        check("Overpass protected-area fallback",overpass.containing_protected_areas(LAT,LON),lambda x:isinstance(x,dict) and "elements" in x),
        check("GDELT forest news",gdelt.forest_news("Kodagu Karnataka","1week"),lambda x:isinstance(x,dict)),
        check("Google News RSS fallback",gnews.forest_news("Kodagu Karnataka","1week"),lambda x:isinstance(x,dict) and "articles" in x),
        check("GFW RADD radar layer metadata",asyncio.sleep(0, result=gfw.tile_layer("wur_radd_alerts")),lambda x:isinstance(x,dict) and "wur_radd_alerts" in x.get("tile_url","")),
    )
    print(json.dumps({"location":{"lat":LAT,"lon":LON},"checks":checks},indent=2))
    core={"Earth Search Sentinel-2","Open-Meteo","MET Norway","NASA GIBS","NASA EONET","NASA POWER","Planetary Computer Sentinel-2","TiTiler Sentinel-2 six-mode rendering","Sentinel-2 filtered date/cloud rendering","Planetary Computer six-mode rendering","Historical Landsat 1987 archive rendering","OSRM patrol matrix + route rendering","NASA GIBS environmental raster rendering","Google News RSS fallback"}
    failed_core=[x for x in checks if x["source"] in core and not x["ok"]]
    if failed_core:
        print("Core public provider smoke failure:",failed_core,file=sys.stderr)
        return 1
    return 0

if __name__=="__main__":
    raise SystemExit(asyncio.run(main()))
