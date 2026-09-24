from __future__ import annotations
import asyncio, json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.models import SourceResult, Provenance, RiskInputs, CarbonRequest, PatrolRequest, WhatIfRequest, ForestDoctorInputs, RecoveryInputs, CorrelationInputs, RegionComparisonRequest
from app.adapters import OpenMeteoAdapter, CopernicusAdapter, SoilGridsAdapter, OverpassAdapter, FIRMSAdapter, ProtectedPlanetAdapter, GDELTAdapter, GFWAdapter
from app.adapters.base import AdapterError
from app.services.layers import LAYER_GROUPS, FEATURES
from app.services.intelligence import risk_score, cascade, intervention, resilience, forest_doctor, recovery, correlations, compare_regions, anomaly_radar
from app.services.carbon import estimate as carbon_estimate
from app.services.patrol import optimize as patrol_optimize
from app.services.nl_query import parse as parse_nl
from app.services.reporting import pdf_report
from app.services.raster_analysis import ndvi_change, RasterInputError

app=FastAPI(title=settings.app_name,version="1.0.0",description="India-first forest intelligence and early-warning platform")

weather=OpenMeteoAdapter(); copernicus=CopernicusAdapter(); soil=SoilGridsAdapter(); overpass=OverpassAdapter(); firms=FIRMSAdapter(); pp=ProtectedPlanetAdapter(); gdelt=GDELTAdapter(); gfw=GFWAdapter()

def prov(source, freshness="UNKNOWN", url=None, observed_at=None, notes=None, resolution_m=None):
    return Provenance(source=source,fetched_at=datetime.now(timezone.utc).isoformat(),observed_at=observed_at,freshness=freshness,source_url=url,notes=notes,resolution_m=resolution_m)

async def wrap(name, coro, freshness, url, resolution_m=None):
    try:
        data=await coro
        observed=None
        if isinstance(data,dict):
            observed=(data.get("current") or {}).get("time") or data.get("datetime")
        return SourceResult(ok=True,data=data,provenance=prov(name,freshness,url,observed,resolution_m=resolution_m))
    except Exception as e:
        return SourceResult(ok=False,data=None,error=str(e),provenance=prov(name,freshness,url,notes="Unavailable; no fallback values were fabricated."))

@app.get("/api/health")
async def health():
    return {"ok":True,"service":settings.app_name,"time":datetime.now(timezone.utc).isoformat(),"environment":settings.environment}

@app.get("/api/features")
def features(): return {"count":len(FEATURES),"features":FEATURES}

@app.get("/api/layers")
def layers(): return {"groups":LAYER_GROUPS,"global_filters":["date_range","source","resolution","freshness","state","district","forest","confidence","severity","cloud_cover","protected_only"]}

@app.get("/api/weather",response_model=SourceResult)
async def weather_ep(lat:float,lon:float): return await wrap("Open-Meteo",weather.current(lat,lon),"FORECAST",weather.source_url)

@app.get("/api/satellite/latest",response_model=SourceResult)
async def sat_ep(lat:float,lon:float,days:int=Query(30,ge=1,le=365),cloud_lt:float=Query(40,ge=0,le=100)):
    return await wrap("Copernicus Sentinel-2 L2A STAC",copernicus.latest_sentinel2(lat,lon,days,cloud_lt),"DYNAMIC_RECENT",copernicus.source_url,10)

@app.get("/api/soil",response_model=SourceResult)
async def soil_ep(lat:float,lon:float): return await wrap("SoilGrids",soil.point(lat,lon),"REFERENCE",soil.source_url,250)

@app.get("/api/human-pressure",response_model=SourceResult)
async def pressure_ep(lat:float,lon:float,radius_m:int=Query(5000,ge=500,le=25000)):
    result=await wrap("OpenStreetMap / Overpass",overpass.pressure(lat,lon,radius_m),"DYNAMIC_RECENT",overpass.source_url)
    if result.ok and isinstance(result.data,dict):
        els=result.data.get("elements",[]); result.data={"count":len(els),"elements":els[:250],"radius_m":radius_m}
    return result

@app.get("/api/fire",response_model=SourceResult)
async def fire_ep(lat:float,lon:float,days:int=Query(1,ge=1,le=5)):
    return await wrap("NASA FIRMS VIIRS NOAA-21 NRT",firms.fires(lat,lon,days=days),"LIVE_NRT",firms.source_url)

@app.get("/api/protected-areas",response_model=SourceResult)
async def protected_ep(page:int=1): return await wrap("Protected Planet API v4",pp.india(page),"REFERENCE",pp.source_url)

@app.get("/api/news",response_model=SourceResult)
async def news_ep(place:str=Query(...,min_length=2),timespan:str="1week"):
    return await wrap("GDELT DOC 2.0",gdelt.forest_news(place,timespan),"DYNAMIC_RECENT",gdelt.source_url)

@app.get("/api/gfw",response_model=SourceResult)
async def gfw_ep(): return await wrap("Global Forest Watch",gfw.metadata(),"DYNAMIC_RECENT",gfw.source_url)

@app.get("/api/investigate")
async def investigate(lat:float,lon:float,place:str="India"):
    tasks={
        "weather":wrap("Open-Meteo",weather.current(lat,lon),"FORECAST",weather.source_url),
        "satellite":wrap("Copernicus Sentinel-2 L2A STAC",copernicus.latest_sentinel2(lat,lon),"DYNAMIC_RECENT",copernicus.source_url,10),
        "soil":wrap("SoilGrids",soil.point(lat,lon),"REFERENCE",soil.source_url,250),
        "human_pressure":wrap("OpenStreetMap / Overpass",overpass.pressure(lat,lon),"DYNAMIC_RECENT",overpass.source_url),
        "fire":wrap("NASA FIRMS",firms.fires(lat,lon),"LIVE_NRT",firms.source_url),
        "news":wrap("GDELT",gdelt.forest_news(place),"DYNAMIC_RECENT",gdelt.source_url),
    }
    vals=await asyncio.gather(*tasks.values())
    return {"location":{"lat":lat,"lon":lon,"place":place},"sources":dict(zip(tasks.keys(),[v.model_dump() for v in vals])),"classification_note":"Observed, derived, forecast and AI-estimated data must remain visually separated."}

@app.post("/api/intelligence/risk")
def risk_ep(x:RiskInputs): return risk_score(x)

@app.post("/api/intelligence/cascade")
def cascade_ep(x:RiskInputs): return cascade(x)

@app.post("/api/intelligence/resilience")
def resilience_ep(x:RiskInputs): return resilience(x)

@app.post("/api/intelligence/intervention")
def intervention_ep(x:RiskInputs): return {"recommendations":intervention(x),"label":"AI_ESTIMATE"}

@app.post("/api/intelligence/what-if")
def what_if(req:WhatIfRequest):
    b=req.base.model_copy(deep=True)
    b.temp_anomaly_c=max(0,min(10,b.temp_anomaly_c+req.temperature_delta_c))
    b.rainfall_deficit_pct=max(0,min(100,b.rainfall_deficit_pct+req.rainfall_delta_pct))
    b.fire_signal=max(0,min(1,b.fire_signal+req.fire_delta))
    b.ndvi_drop=max(0,min(1,b.ndvi_drop+req.ndvi_delta))
    return {"baseline":risk_score(req.base),"scenario":risk_score(b),"scenario_inputs":b.model_dump(),"label":"AI_ESTIMATE"}


@app.post("/api/intelligence/forest-doctor")
def forest_doctor_ep(x:ForestDoctorInputs): return forest_doctor(x)

@app.post("/api/intelligence/recovery")
def recovery_ep(x:RecoveryInputs): return recovery(x)

@app.post("/api/intelligence/correlation")
def correlation_ep(x:CorrelationInputs):
    try: return correlations(x)
    except ValueError as e: raise HTTPException(422,str(e))

@app.post("/api/intelligence/compare-regions")
def compare_ep(x:RegionComparisonRequest): return compare_regions(x)

@app.post("/api/intelligence/anomaly-radar")
def anomaly_ep(signals:dict[str,float]): return anomaly_radar(signals)

@app.post("/api/analysis/ndvi-change")
async def ndvi_change_ep(before:UploadFile=File(...),after:UploadFile=File(...),threshold:float=Query(.2,ge=.01,le=1)):
    try: return ndvi_change(await before.read(),await after.read(),threshold)
    except RasterInputError as e: raise HTTPException(422,str(e))

@app.post("/api/carbon")
def carbon_ep(req:CarbonRequest): return carbon_estimate(req)

@app.post("/api/patrol")
def patrol_ep(req:PatrolRequest): return patrol_optimize(req)

@app.get("/api/query")
def nl_query(q:str=Query(...,min_length=3)): return parse_nl(q)

@app.post("/api/report")
def report(payload:dict):
    title=payload.get("title","VanRakshak Investigation Report")
    lines=[f"Generated: {datetime.now(timezone.utc).isoformat()}"]
    for k,v in payload.items():
        if k!="title": lines.append(f"{k}: {json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v}")
    return Response(pdf_report(title,lines),media_type="application/pdf",headers={"Content-Disposition":"attachment; filename=vanrakshak-report.pdf"})

PROJECT_ROOT=Path(__file__).resolve().parents[2]
WEB=PROJECT_ROOT/"web"
if not WEB.exists():
    WEB=Path("/web")
if WEB.exists():
    app.mount("/static",StaticFiles(directory=str(WEB)),name="static")

@app.get("/")
def root():
    p=WEB/"index.html"
    return FileResponse(str(p)) if p.exists() else {"message":"VanRakshak AI API","docs":"/docs"}
