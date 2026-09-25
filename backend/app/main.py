from __future__ import annotations
import asyncio, json, os, math
import httpx
from datetime import datetime, timedelta, timezone
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import (
    SourceResult, Provenance, RiskInputs, CarbonRequest, PatrolRequest, WhatIfRequest,
    ForestDoctorInputs, RecoveryInputs, CorrelationInputs, RegionComparisonRequest,
    ThreatPredictionRequest, PersistInvestigationRequest,
)
from app.adapters import (
    OpenMeteoAdapter, CopernicusAdapter, SoilGridsAdapter, OverpassAdapter,
    FIRMSAdapter, ProtectedPlanetAdapter, GDELTAdapter, GFWAdapter,
    EarthSearchAdapter, NominatimAdapter, EarthEngineAdapter, Sentinel1ASFAdapter, OSRMAdapter,
    BhuvanAdapter, MOSDACAdapter, GIBSAdapter, EONETAdapter, PhotonAdapter, NASAPowerAdapter, PlanetaryComputerAdapter, GoogleNewsRSSAdapter, METNorwayAdapter, USGSLandsatAdapter, GCPLandsatAdapter,
)
from app.adapters.base import AdapterError
from app.services.layers import LAYER_GROUPS, FEATURES
from app.services.intelligence import (
    risk_score, cascade, intervention, resilience, forest_doctor, recovery,
    correlations, compare_regions, anomaly_radar,
)
from app.services.carbon import estimate as carbon_estimate
from app.services.patrol import optimize as patrol_optimize
from app.services.nl_query import parse as parse_nl
from app.services.reporting import pdf_report, investigation_pdf
from app.services.raster_analysis import ndvi_change, RasterInputError
from app.services.fragmentation import metrics as fragmentation_metrics, FragmentationInputError
from app.services.prediction import predict as predict_threat
from app.services.climate import anomaly as climate_anomaly
from app.services import historical_imagery
from app.services.historical_landsat_tiles import render_png as render_historical_landsat_png, HistoricalTileError
from app.services.tiles import satellite_layer, compare_layers, gfw_layer
from app.services.remote_change import analyze as remote_change_analyze, RemoteChangeError, scene_summary, recovery_from_series
from app.services.sar_change import analyze as sar_change_analyze, SARChangeError
from app.services.evidence import build_chain, partial_risk, pressure_context
from app.services.model_runtime import status as change_model_status
from app.services.feature_status import FEATURE_CAPABILITIES
from app.services.source_health import snapshot as source_health_snapshot
from app.services.alerts import compose_patrol_alert
from app.services.cache import cached_async, cache_stats, clear_cache_async, redis_ping
from app.services.fallbacks import (
    geocode_search as fallback_geocode_search,
    reverse_geocode as fallback_reverse_geocode,
    fire_rows as fallback_fire_rows,
    protected_context as fallback_protected_context,
    provider_strategy,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_init_db:
        try:
            from app.db import init_db
            init_db()
        except Exception:
            pass
    yield

app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="India-first satellite forest intelligence, investigation and early-warning platform",
    lifespan=lifespan,
)

@app.exception_handler(AdapterError)
async def provider_error_handler(request, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc), "status": "PROVIDER_UNAVAILABLE"})

@app.exception_handler(httpx.RequestError)
async def upstream_transport_error_handler(request, exc):
    return JSONResponse(status_code=503, content={"detail": "The upstream provider could not be reached. Please retry.", "status": "PROVIDER_UNAVAILABLE"})


weather = OpenMeteoAdapter(); copernicus = CopernicusAdapter(); soil = SoilGridsAdapter()
overpass = OverpassAdapter(); firms = FIRMSAdapter(); pp = ProtectedPlanetAdapter()
gdelt = GDELTAdapter(); gfw = GFWAdapter(); earth = EarthSearchAdapter()
geocoder = NominatimAdapter(); photon = PhotonAdapter(); ee = EarthEngineAdapter(); s1 = Sentinel1ASFAdapter(); osrm = OSRMAdapter()
bhuvan = BhuvanAdapter(); mosdac = MOSDACAdapter(); gibs = GIBSAdapter(); eonet = EONETAdapter(); power = NASAPowerAdapter(); pc = PlanetaryComputerAdapter(); gnews = GoogleNewsRSSAdapter(); metno = METNorwayAdapter(); usgs_landsat = USGSLandsatAdapter(); gcp_landsat = GCPLandsatAdapter()


def prov(source, freshness="UNKNOWN", url=None, observed_at=None, notes=None, resolution_m=None):
    return Provenance(
        source=source, fetched_at=datetime.now(timezone.utc).isoformat(), observed_at=observed_at,
        freshness=freshness, source_url=url, notes=notes, resolution_m=resolution_m,
    )


async def wrap(name, coro, freshness, url, resolution_m=None):
    try:
        data = await coro
        observed = None
        if isinstance(data, dict):
            observed = (data.get("current") or {}).get("time") or data.get("datetime")
        return SourceResult(ok=True, data=data, provenance=prov(name, freshness, url, observed, resolution_m=resolution_m))
    except Exception as e:
        return SourceResult(
            ok=False, data=None, error=str(e),
            provenance=prov(name, freshness, url, notes="Unavailable; no fallback environmental values were fabricated."),
        )


async def climate_anomaly_real(lat: float, lon: float, window_days: int = 30, baseline_years: int = 5):
    errors=[]
    for provider,label in ((weather,"Open-Meteo Historical/Reanalysis"),(power,"NASA POWER Daily Meteorology")):
        try:
            result=await climate_anomaly(provider,lat,lon,window_days,baseline_years)
            result["provider_fallback_used"]=bool(errors)
            if errors:
                result["provider_trace"]=errors
            return result
        except Exception as exc:
            errors.append(f"{label}: {exc}")
    raise RuntimeError("All real historical climate providers failed: "+" | ".join(errors))


async def historical_climate_daily_real(lat: float, lon: float, start: str, end: str):
    errors=[]
    for provider,label in ((weather,"Open-Meteo Historical/Reanalysis"),(power,"NASA POWER Daily Meteorology")):
        try:
            data=await provider.historical_daily(lat,lon,start,end)
            return data,label,errors
        except Exception as exc:
            errors.append(f"{label}: {exc}")
    raise RuntimeError("All real historical climate providers failed: "+" | ".join(errors))


async def fire_source_result(lat: float, lon: float, days: int = 1):
    try:
        info = await fallback_fire_rows(firms, eonet, lat, lon, days)
        url = firms.source_url if not info.get("degraded") else eonet.source_url
        notes = info.get("note")
        if info.get("errors"):
            notes = (notes or "") + " | Fallback trace: " + "; ".join(info["errors"])
        return SourceResult(
            ok=True,
            data=info.get("rows") or [],
            provenance=prov(info["source"], info["freshness"], url, notes=notes),
        )
    except Exception as exc:
        return SourceResult(
            ok=False, data=None, error=str(exc),
            provenance=prov("NASA fire intelligence", "UNKNOWN", firms.source_url, notes="FIRMS and no-key EONET fallback were both unavailable."),
        )


async def weather_source_result(lat: float, lon: float):
    errors=[]
    try:
        data=await weather.current(lat,lon)
        observed=(data.get("current") or {}).get("time") if isinstance(data,dict) else None
        return SourceResult(
            ok=True,data=data,
            provenance=prov("Open-Meteo","FORECAST",weather.source_url,observed),
        )
    except Exception as exc:
        errors.append(f"Open-Meteo: {exc}")
    try:
        data=await metno.current(lat,lon)
        observed=(data.get("current") or {}).get("time") if isinstance(data,dict) else None
        return SourceResult(
            ok=True,data=data,
            provenance=prov(
                "MET Norway Locationforecast","FORECAST",metno.source_url,observed,
                notes="Open-Meteo unavailable; independent credential-free weather fallback used. "+"; ".join(errors),
            ),
        )
    except Exception as exc:
        errors.append(f"MET Norway: {exc}")
    return SourceResult(
        ok=False,data=None,error="; ".join(errors),
        provenance=prov(
            "Weather intelligence","UNKNOWN",weather.source_url,
            notes="Both real weather providers unavailable; no weather values fabricated.",
        ),
    )


async def climate_anomaly_source(lat: float, lon: float, window_days: int = 30, baseline_years: int = 5):
    errors=[]
    try:
        result=await climate_anomaly(weather,lat,lon,window_days,baseline_years)
        result["provider_chain"]=["Open-Meteo Historical/Reanalysis"]
        return result
    except Exception as exc:
        errors.append(f"Open-Meteo: {exc}")
    try:
        result=await climate_anomaly(power,lat,lon,window_days,baseline_years)
        result["provider_chain"]=["Open-Meteo failed","NASA POWER Daily Meteorology"]
        result["fallback_used"]=True
        result["fallback_trace"]=errors
        return result
    except Exception as exc:
        errors.append(f"NASA POWER: {exc}")
        raise AdapterError("Historical climate providers unavailable: "+"; ".join(errors))


async def climate_history_source(lat: float, lon: float, start: str, end: str):
    errors=[]
    try:
        data=await weather.historical_daily(lat,lon,start,end)
        return {"data":data,"source":"Open-Meteo Historical/Reanalysis","fallback_used":False}
    except Exception as exc:
        errors.append(f"Open-Meteo: {exc}")
    try:
        data=await power.historical_daily(lat,lon,start,end)
        return {"data":data,"source":"NASA POWER Daily Meteorology","fallback_used":True,"fallback_trace":errors}
    except Exception as exc:
        errors.append(f"NASA POWER: {exc}")
        raise AdapterError("Historical climate providers unavailable: "+"; ".join(errors))


async def news_source_result(place: str, timespan: str = "1week"):
    async def attempt(label: str, url: str, coro):
        try:
            return True,label,url,await coro,None
        except Exception as exc:
            return False,label,url,None,str(exc)

    tasks={
        asyncio.create_task(attempt("GDELT DOC 2.0",gdelt.source_url,gdelt.forest_news(place,timespan))),
        asyncio.create_task(attempt("Google News RSS",gnews.source_url,gnews.forest_news(place,timespan))),
    }
    errors=[]
    pending=set(tasks)
    try:
        async with asyncio.timeout(6.0):
            while pending:
                done,pending=await asyncio.wait(pending,return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    ok,label,url,data,error=await task
                    if ok:
                        for p in pending:
                            p.cancel()
                        if pending:
                            await asyncio.gather(*pending,return_exceptions=True)
                        notes=None
                        if label!="GDELT DOC 2.0":
                            notes="Fastest responsive real news provider selected; GDELT remains available when responsive."
                        return SourceResult(
                            ok=True,data=data,
                            provenance=prov(label,"DYNAMIC_RECENT",url,notes=notes),
                        )
                    errors.append(f"{label}: {error}")
    except TimeoutError:
        errors.append("News providers exceeded 6 second response budget")
    finally:
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending,return_exceptions=True)

    return SourceResult(
        ok=False,data=None,error="; ".join(errors),
        provenance=prov(
            "Forest news intelligence","UNKNOWN",gdelt.source_url,
            notes="No news provider responded within the bounded request budget; no headlines were fabricated.",
        ),
    )


async def protected_source_result(lat: float, lon: float):
    try:
        ctx = await fallback_protected_context(overpass, ee, lat, lon)
        url = overpass.source_url if ctx.get("degraded") else ee.source_url
        return SourceResult(
            ok=True,
            data=ctx,
            provenance=prov(ctx["source"], "REFERENCE", url, notes=ctx.get("note")),
        )
    except Exception as exc:
        return SourceResult(
            ok=False, data=None, error=str(exc),
            provenance=prov("Protected-area intelligence", "REFERENCE", pp.source_url, notes="Authoritative and public fallback sources were unavailable."),
        )


async def geocode_source_result(q: str):
    try:
        result = await fallback_geocode_search(geocoder, photon, q, 5)
        return SourceResult(
            ok=True, data=result["data"],
            provenance=prov(result["source"], "DYNAMIC_RECENT", geocoder.source_url if not result["degraded"] else photon.source_url,
                            notes=("Fallback used. " + "; ".join(result["errors"])) if result["degraded"] else None),
        )
    except Exception as exc:
        return SourceResult(ok=False, data=None, error=str(exc), provenance=prov("OSM geocoding", "DYNAMIC_RECENT", geocoder.source_url))


async def reverse_source_result(lat: float, lon: float):
    try:
        result = await fallback_reverse_geocode(geocoder, photon, lat, lon)
        return SourceResult(
            ok=True, data=result["data"],
            provenance=prov(result["source"], "DYNAMIC_RECENT", geocoder.source_url if not result["degraded"] else photon.source_url,
                            notes=("Fallback used. " + "; ".join(result["errors"])) if result["degraded"] else None),
        )
    except Exception as exc:
        return SourceResult(ok=False, data=None, error=str(exc), provenance=prov("OSM reverse geocoding", "DYNAMIC_RECENT", geocoder.source_url))


async def investigation_sources(lat: float, lon: float, place: str):
    key=f"investigation:{round(lat,4)}:{round(lon,4)}:{place.lower().strip()[:80]}"

    async def bounded(coro, source: str, freshness: str, url: str, timeout_s: float):
        try:
            return await asyncio.wait_for(coro,timeout=timeout_s)
        except TimeoutError:
            return SourceResult(
                ok=False,data=None,error=f"{source} exceeded {timeout_s:g}s investigation response budget",
                provenance=prov(
                    source,freshness,url,
                    notes="Provider was bounded so one slow upstream cannot block the full investigation dashboard.",
                ),
            )
        except Exception as exc:
            return SourceResult(
                ok=False,data=None,error=str(exc),
                provenance=prov(source,freshness,url,notes="Provider failed during bounded investigation collection."),
            )

    async def produce():
        specs = {
            "weather": (weather_source_result(lat,lon),"Weather intelligence","FORECAST",weather.source_url,8.0),
            "satellite": (wrap("Copernicus Sentinel-2 L2A STAC", copernicus.latest_sentinel2(lat, lon), "DYNAMIC_RECENT", copernicus.source_url, 10),"Copernicus Sentinel-2 L2A STAC","DYNAMIC_RECENT",copernicus.source_url,8.0),
            "earth_search": (wrap("Earth Search Sentinel-2 L2A", earth.latest_sentinel2(lat, lon), "DYNAMIC_RECENT", earth.source_url, 10),"Earth Search Sentinel-2 L2A","DYNAMIC_RECENT",earth.source_url,8.0),
            "planetary_computer": (wrap("Planetary Computer Sentinel-2 L2A", pc.latest_sentinel2(lat, lon), "DYNAMIC_RECENT", pc.source_url, 10),"Planetary Computer Sentinel-2 L2A","DYNAMIC_RECENT",pc.source_url,8.0),
            "sentinel1": (wrap("ASF Sentinel-1 Search", s1.latest(lat, lon), "DYNAMIC_RECENT", s1.source_url, 10),"ASF Sentinel-1 Search","DYNAMIC_RECENT",s1.source_url,8.0),
            "soil": (wrap("SoilGrids", soil.point(lat, lon), "REFERENCE", soil.source_url, 250),"SoilGrids","REFERENCE",soil.source_url,8.0),
            "human_pressure": (wrap("OpenStreetMap / Overpass", overpass.pressure(lat, lon), "DYNAMIC_RECENT", overpass.source_url),"OpenStreetMap / Overpass","DYNAMIC_RECENT",overpass.source_url,8.0),
            "fire": (fire_source_result(lat, lon, 1),"NASA fire intelligence","DYNAMIC_RECENT",firms.source_url,8.0),
            "natural_events": (wrap("NASA EONET", eonet.events(lat, lon, days=30, radius_deg=3, limit=50), "DYNAMIC_RECENT", eonet.source_url),"NASA EONET","DYNAMIC_RECENT",eonet.source_url,8.0),
            "protected_area": (protected_source_result(lat, lon),"Protected-area intelligence","REFERENCE",pp.source_url,8.0),
            "news": (news_source_result(place),"Forest news intelligence","DYNAMIC_RECENT",gdelt.source_url,7.0),
            "reverse_geocode": (reverse_source_result(lat, lon),"OSM reverse geocoding","DYNAMIC_RECENT",geocoder.source_url,8.0),
        }
        vals=await asyncio.gather(*[
            bounded(coro,source,freshness,url,timeout_s)
            for coro,source,freshness,url,timeout_s in specs.values()
        ])
        return dict(zip(specs.keys(),[v.model_dump() for v in vals]))

    return await cached_async(key,settings.cache_ttl_s,produce)


@app.get("/api/build-info")
def build_info():
    return {
        "git_sha": os.getenv("RAILWAY_GIT_COMMIT_SHA"),
        "git_branch": os.getenv("RAILWAY_GIT_BRANCH"),
        "deployment_id": os.getenv("RAILWAY_DEPLOYMENT_ID"),
        "snapshot_id": os.getenv("RAILWAY_SNAPSHOT_ID"),
        "environment": settings.environment,
        "service": settings.app_name,
    }


@app.get("/api/health")
async def health():
    return {
        "ok": True, "service": settings.app_name, "version": "2.0.0",
        "time": datetime.now(timezone.utc).isoformat(), "environment": settings.environment,
        "capabilities": {
            "firms_configured": bool(settings.firms_map_key),
            "protected_planet_configured": bool(settings.protected_planet_token),
            "earth_engine_project": bool(settings.google_cloud_project),
            "earth_engine_api_repo": ee.api_repo_url,
            "titiler": settings.titiler_public_url,
            "database": settings.database_url.split(":",1)[0],
            "credential_free_fallbacks": True,
            "gibs": True,
            "eonet": True,
            "nasa_power": True,
            "met_norway": True,
            "planetary_computer": True,
            "photon_geocoder": True,
        },
    }


@app.head("/api/health", include_in_schema=False)
async def health_head():
    return Response(status_code=200)


@app.get("/api/ready")
async def ready():
    checks={"static":False,"database":False}
    try:
        checks["static"]=(Path("/web/index.html").exists() or Path("web/index.html").exists())
    except Exception:
        checks["static"]=False
    try:
        from sqlalchemy import text as sql_text
        from app.db import engine
        with engine.connect() as conn:
            conn.execute(sql_text("SELECT 1"))
        checks["database"]=True
    except Exception as exc:
        checks["database_error"]=str(exc)

    production=settings.environment.lower() in {"production","prod","railway"}
    if production:
        redis_result=await redis_ping()
        checks["redis"]=bool(redis_result.get("ok"))
        if not checks["redis"]:
            checks["redis_error"]=redis_result.get("error")

        checks["titiler"]=False
        try:
            url=settings.titiler_internal_url.rstrip("/")+"/"
            async with httpx.AsyncClient(timeout=3.0,follow_redirects=True) as client:
                response=await client.get(url)
            checks["titiler"]=response.status_code < 500
            checks["titiler_status"]=response.status_code
        except Exception as exc:
            checks["titiler_error"]=str(exc)
    else:
        checks["redis"]="OPTIONAL_IN_DEVELOPMENT"
        checks["titiler"]="OPTIONAL_IN_DEVELOPMENT"

    required=["static","database"] + (["redis","titiler"] if production else [])
    ok=all(bool(checks.get(k)) for k in required)
    payload={
        "ok":ok,
        "service":settings.app_name,
        "environment":settings.environment,
        "required_checks":required,
        "checks":checks,
        "time":datetime.now(timezone.utc).isoformat(),
    }
    if not ok:
        raise HTTPException(503,payload)
    return payload


@app.get("/api/features")
def features(): return {"count": len(FEATURES), "features": FEATURES}

@app.get("/api/cache/status")
def cache_status():
    return {"ttl_s":settings.cache_ttl_s,**cache_stats()}

@app.post("/api/cache/clear")
async def cache_clear():
    await clear_cache_async()
    return {"ok":True,**cache_stats()}


@app.get("/api/features/status")
def feature_status(): return {"count":len(FEATURE_CAPABILITIES),"features":FEATURE_CAPABILITIES}


@app.get("/api/demo-scenarios")
def demo_scenarios():
    candidates=[
        Path(__file__).resolve().parents[2]/"config"/"demo_scenarios.json",
        Path("/config/demo_scenarios.json"),
    ]
    for path in candidates:
        if path.exists():
            data=json.loads(path.read_text(encoding="utf-8"))
            return {
                **data,
                "count":len(data.get("scenarios") or []),
                "note":"Scenario dates and scene IDs are preflight-verified inputs; environmental outputs are still computed from real providers and are never fabricated.",
            }
    raise HTTPException(503,"Demo scenario manifest unavailable")


@app.get("/api/source-health")
async def source_health(lat: float = 12.9716, lon: float = 77.5946):
    key=f"source-health:{round(lat,3)}:{round(lon,3)}"
    async def produce():
        return await source_health_snapshot({
            "copernicus": copernicus, "earth": earth, "weather": weather, "soil": soil,
            "geocoder": geocoder, "photon": photon, "s1": s1, "firms": firms, "pp": pp, "ee": ee,
            "gibs": gibs, "eonet": eonet, "power": power, "pc": pc, "gnews": gnews, "metno": metno,
        }, lat, lon)
    return await cached_async(key,60,produce)


@app.get("/api/layers")
def layers():
    return {
        "groups": LAYER_GROUPS,
        "global_filters": [
            "date_range", "source", "layer_type", "resolution", "freshness",
            "confidence", "cloud_cover",
        ],
        "earth_engine": ee.catalog(),
    }


@app.get("/api/integrations/open-source")
def open_source_integrations():
    candidates=[
        Path(__file__).resolve().parents[2]/"config"/"open_source_integrations.json",
        Path("/config/open_source_integrations.json"),
    ]
    for path in candidates:
        if path.exists():
            data=json.loads(path.read_text(encoding="utf-8"))
            items=data.get("integrations") or []
            return {
                **data,
                "count":len(items),
                "runtime_or_integrated":sum(1 for x in items if x.get("status") in {"RUNTIME","API_INTEGRATED"}),
            }
    raise HTTPException(503,"Open-source integration registry unavailable")


@app.get("/api/geocode")
async def geocode(q: str = Query(..., min_length=2)):
    return await geocode_source_result(q)


@app.get("/api/reverse-geocode")
async def reverse_geocode(lat: float, lon: float):
    return await reverse_source_result(lat, lon)


@app.get("/api/weather", response_model=SourceResult)
async def weather_ep(lat: float, lon: float):
    return await weather_source_result(lat,lon)


@app.get("/api/climate/anomaly")
async def climate_anomaly_ep(lat: float, lon: float, window_days: int = Query(30, ge=7, le=90), baseline_years: int = Query(5, ge=2, le=15)):
    try:
        return await climate_anomaly_real(lat, lon, window_days, baseline_years)
    except Exception as e:
        raise HTTPException(503, str(e))


@app.get("/api/satellite/latest", response_model=SourceResult)
async def sat_ep(lat: float, lon: float, days: int = Query(30, ge=1, le=365), cloud_lt: float = Query(40, ge=0, le=100)):
    return await wrap("Copernicus Sentinel-2 L2A STAC", copernicus.latest_sentinel2(lat, lon, days, cloud_lt), "DYNAMIC_RECENT", copernicus.source_url, 10)


@app.get("/api/satellite/sentinel1", response_model=SourceResult)
async def sentinel1_ep(lat: float, lon: float, days: int = Query(30, ge=1, le=365)):
    return await wrap("ASF Sentinel-1 Search", s1.latest(lat, lon, days), "DYNAMIC_RECENT", s1.source_url, 10)


@app.get("/api/satellite/planetary-computer", response_model=SourceResult)
async def planetary_computer_satellite_ep(lat: float, lon: float, days: int = Query(45, ge=1, le=365), cloud_lt: float = Query(80, ge=0, le=100)):
    return await wrap("Microsoft Planetary Computer Sentinel-2 L2A", pc.latest_sentinel2(lat,lon,days,cloud_lt), "DYNAMIC_RECENT", pc.source_url, 10)


@app.get("/api/satellite/landsat", response_model=SourceResult)
async def landsat_ep(lat: float, lon: float, days: int = Query(90, ge=1, le=730), cloud_lt: float = Query(60, ge=0, le=100)):
    return await wrap("Earth Search Landsat Collection 2 L2", earth.latest_landsat(lat, lon, days, cloud_lt), "DYNAMIC_RECENT", earth.source_url, 30)


@app.get("/api/map/satellite-layer")
async def map_satellite_layer(
    lat: float, lon: float,
    mode: str = Query("true_color", pattern="^(true_color|false_color|ndvi|ndmi|nbr|ndwi)$"),
    days: int = Query(45, ge=1, le=365), cloud_lt: float = Query(50, ge=0, le=100),
    start_date: str | None = None, end_date: str | None = None,
):
    start_dt=end_dt=None
    try:
        if start_date:
            start_dt=datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        if end_date:
            end_dt=datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc) + timedelta(days=1)
        if start_dt and end_dt and start_dt >= end_dt:
            raise ValueError("start must be before end")
    except Exception:
        raise HTTPException(422,"start_date/end_date must use YYYY-MM-DD and start must be before end")
    primary_error=None
    try:
        if end_dt and end_dt <= historical_imagery.SENTINEL_START:
            target=(end_dt-timedelta(days=1))
            if start_dt:
                target=start_dt+(end_dt-start_dt)/2
            result=await historical_imagery.dated_scene(
                earth,pc,lat,lon,target,mode,max(35,min(days,365)),cloud_lt,usgs_landsat,gcp_landsat
            )
            if not result:
                raise AdapterError("No historical Landsat observation was found near the selected date range")
            result["fallback_used"]=False
            result["provider_chain"]=["USGS Landsat STAC","Google public Landsat mirror"]
            result["filter_note"]="Historical archive uses the nearest available real Landsat capture and reports its actual observation date."
            return result
        result=await satellite_layer(earth, lat, lon, mode, days, cloud_lt, start_dt, end_dt)
        result["fallback_used"]=False
        result["provider_chain"]=["Earth Search","TiTiler"]
        return result
    except Exception as exc:
        primary_error=str(exc)

    # Exact scientific fallback: the same Sentinel-2 L2A bands and formulas,
    # rendered by Microsoft Planetary Computer instead of our TiTiler.
    search_end=end_dt or datetime.now(timezone.utc)
    search_start=start_dt or (search_end-timedelta(days=days))
    try:
        collection="landsat-c2-l2" if search_end < historical_imagery.SENTINEL_START else "sentinel-2-l2a"
        pdata=await pc.search_optical(lat,lon,search_start,search_end,cloud_lt,30,collection)
        pitems=pdata.get("features") or []
        if pitems:
            def pc_key(item):
                p=item.get("properties") or {}
                cloud=p.get("eo:cloud_cover")
                dt=str(p.get("datetime") or "")
                try:
                    ts=datetime.fromisoformat(dt.replace("Z","+00:00")).timestamp() if dt else 0.0
                except Exception:
                    ts=0.0
                return (-ts,float(cloud if cloud is not None else 1000))
            pitems.sort(key=pc_key)
            fallback=await pc.tile_spec(pitems[0],mode)
            fallback["fallback_reason"]=primary_error
            fallback["provider_chain"]=["Earth Search/TiTiler failed","Microsoft Planetary Computer"]
            fallback["filter_note"]="Requested spectral mode from the selected satellite archive; cloud/date filters are preserved."
            return fallback
        primary_error += " | Planetary Computer: no matching Sentinel-2 scene"
    except Exception as exc:
        primary_error += f" | Planetary Computer: {exc}"

    # Tertiary visualization fallbacks are used only where the product is
    # scientifically equivalent enough to keep the UI useful without
    # pretending a different metric is NDMI/NBR/NDWI.
    gibs_by_mode={
        "true_color":"viirs_snpp_true_color",
        "false_color":"viirs_snpp_false_color",
        "ndvi":"modis_terra_ndvi_8day",
    }
    if mode in gibs_by_mode:
        try:
            fallback_date=end_date or (datetime.now(timezone.utc)-timedelta(days=2)).date().isoformat()
            spec=gibs.tile_spec(gibs_by_mode[mode],fallback_date)
            return {
                **spec,"mode":mode,"fallback_used":True,"fallback_reason":primary_error,
                "observed_at":spec.get("date"),"item_id":None,
                "provider_chain":["Earth Search/TiTiler failed","Planetary Computer failed","NASA GIBS"],
                "filter_note":"NASA GIBS fallback is real imagery. It does not apply the Sentinel-2 cloud threshold and may have coarser resolution.",
            }
        except Exception as exc:
            primary_error += f" | NASA GIBS: {exc}"

    raise HTTPException(503,f"No real renderer could satisfy satellite mode '{mode}': {primary_error}")


@app.get("/api/map/satellite-modes/status")
async def satellite_modes_status(
    lat: float, lon: float,
    days: int = Query(45, ge=1, le=365),
    cloud_lt: float = Query(60, ge=0, le=100),
    start_date: str | None = None, end_date: str | None = None,
):
    """Render-probe all Sentinel-2 modes through the same TiTiler path used by the UI."""
    try:
        end_dt=datetime.now(timezone.utc)
        start_dt=end_dt-timedelta(days=days)
        if start_date:
            start_dt=datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        if end_date:
            end_dt=datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)+timedelta(days=1)
        if start_dt >= end_dt:
            raise ValueError("start must be before end")
    except Exception:
        raise HTTPException(422,"start_date/end_date must use YYYY-MM-DD and start must be before end")

    data=await earth.search(lat,lon,start_dt,end_dt,"sentinel-2-l2a",cloud_lt,60)
    features=data.get("features") or []
    if not features:
        raise HTTPException(404,"No suitable Sentinel-2 L2A scene found for the requested filters")
    def scene_key(item):
        p=item.get("properties") or {}
        return (float(p.get("eo:cloud_cover") if p.get("eo:cloud_cover") is not None else 1000),str(p.get("datetime") or ""))
    item=sorted(features,key=scene_key)[0]

    zoom=10
    n=2**zoom
    x=int((lon+180.0)/360.0*n)
    lat_rad=math.radians(max(-85.05112878,min(85.05112878,lat)))
    y=int((1.0-math.asinh(math.tan(lat_rad))/math.pi)/2.0*n)
    x=max(0,min(n-1,x)); y=max(0,min(n-1,y))

    public_base=settings.titiler_public_url.rstrip("/")
    internal_base=settings.titiler_internal_url.rstrip("/")
    modes=("true_color","false_color","ndvi","ndmi","nbr","ndwi")
    async def probe(mode):
        try:
            spec=earth.tile_spec(item,mode)
            tile=spec["tile_url"].replace(public_base,internal_base,1)
            tile=tile.replace("{z}",str(zoom)).replace("{x}",str(x)).replace("{y}",str(y))
            async with httpx.AsyncClient(timeout=35.0,follow_redirects=True) as client:
                r=await client.get(tile)
            ctype=(r.headers.get("content-type") or "").lower()
            ok=r.status_code==200 and ctype.startswith("image/") and len(r.content)>100
            return {
                "mode":mode,"ok":ok,"http_status":r.status_code,"content_type":ctype,
                "bytes":len(r.content),"item_id":spec.get("item_id"),
                "observed_at":spec.get("observed_at"),"cloud_cover":spec.get("cloud_cover"),
                "resolution_m":spec.get("resolution_m"),
                "error":None if ok else (r.text[:240] if "text" in ctype or "json" in ctype else "Tile response was not a valid image"),
            }
        except Exception as exc:
            return {"mode":mode,"ok":False,"http_status":None,"content_type":None,"bytes":0,"error":str(exc)}
    results=await asyncio.gather(*(probe(m) for m in modes))
    return {
        "ok":all(x["ok"] for x in results),
        "scene_id":item.get("id"),
        "scene_datetime":(item.get("properties") or {}).get("datetime"),
        "cloud_cover":(item.get("properties") or {}).get("eo:cloud_cover"),
        "tile_probe":{"z":zoom,"x":x,"y":y},
        "modes":results,
        "source":"Element 84 Earth Search / Sentinel-2 L2A via TiTiler",
        "rule":"A satellite mode is healthy only when the actual raster tile endpoint returns a non-empty image.",
    }



@app.get("/api/historical/landsat-tile/{product_id}/{mode}/{z}/{x}/{y}.png")
async def historical_landsat_tile(product_id: str, mode: str, z: int, x: int, y: int):
    if mode not in {"true_color","false_color","ndvi","ndmi","nbr","ndwi"}:
        raise HTTPException(422,"Unsupported historical Landsat mode")
    if z < 0 or z > 14:
        raise HTTPException(422,"Historical Landsat zoom must be between 0 and 14")
    try:
        metadata=await gcp_landsat.metadata(product_id)
        urls=gcp_landsat.asset_urls(product_id)
        png=await asyncio.to_thread(render_historical_landsat_png,urls,metadata,mode,z,x,y)
        return Response(
            content=png,media_type="image/png",
            headers={"Cache-Control":"public, max-age=86400, stale-while-revalidate=604800"},
        )
    except HistoricalTileError as exc:
        raise HTTPException(502,str(exc))

@app.get("/api/map/compare")
async def map_compare(
    lat: float, lon: float, before_date: str, after_date: str,
    mode: str = Query("true_color", pattern="^(true_color|false_color|ndvi|ndmi|nbr|ndwi)$"),
    window_days: int = Query(35, ge=3, le=90), cloud_lt: float = Query(60, ge=0, le=100),
):
    try:
        b = datetime.fromisoformat(before_date).replace(tzinfo=timezone.utc)
        a = datetime.fromisoformat(after_date).replace(tzinfo=timezone.utc)
    except Exception:
        raise HTTPException(422, "Dates must use YYYY-MM-DD")
    try:
        result = await historical_imagery.compare(earth, pc, lat, lon, b, a, mode, window_days, cloud_lt, usgs_landsat, gcp_landsat)
        if result is None:
            raise HTTPException(404, "No cloud-filtered scene found near one or both dates. Widen the date window or cloud threshold.")
        return result
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/api/time-machine")
async def time_machine(
    lat: float, lon: float, start: str, end: str,
    cloud_lt: float = Query(60, ge=0, le=100), limit: int = Query(50, ge=1, le=100),
):
    try:
        s = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
        e = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
    except Exception:
        raise HTTPException(422, "start/end must use YYYY-MM-DD")
    try:
        return await historical_imagery.timeline(earth, pc, lat, lon, s, e, cloud_lt, limit, usgs_landsat, gcp_landsat)
    except ValueError as exc:
        raise HTTPException(422, str(exc))



@app.get("/api/map/gfw-layer")
def map_gfw_layer(
    dataset: str = "gfw_integrated_alerts", start_date: str | None = None,
    end_date: str | None = None, confidence: str = Query("high", pattern="^(low|nominal|high)$"),
):
    try:
        return gfw_layer(gfw, dataset, start_date, end_date, confidence)
    except AdapterError as e:
        raise HTTPException(422, str(e))


@app.get("/api/earth-engine/catalog")
def earth_engine_catalog():
    return {"layers": ee.catalog(), "requires_auth": True, "source": ee.source_url}


@app.get("/api/earth-engine/layer/{layer_id}")
def earth_engine_layer(layer_id: str, lat: float | None = None, lon: float | None = None, days: int = Query(30, ge=1, le=3650)):
    try:
        return ee.tile(layer_id, lat, lon, days)
    except AdapterError as primary_error:
        # Public, credential-free fallbacks for dashboard raster layers. Keep
        # provenance explicit: these substitutes remain useful without claiming
        # they are the exact Earth Engine product requested.
        fallback_date=(datetime.now(timezone.utc)-timedelta(days=2)).date().isoformat()
        try:
            if layer_id in {"dynamic_world_trees","dynamic_world_label","hansen_treecover"}:
                spec=gfw_layer(gfw,"umd_tree_cover_density_2000",None,None,"high")
                return {
                    **spec,
                    "requested_layer_id":layer_id,
                    "fallback_used":True,
                    "fallback_reason":str(primary_error),
                    "fallback_semantics":"Tree-cover reference; not Dynamic World land-cover classification.",
                    "source":"Global Forest Watch tree-cover density reference",
                }
            if layer_id=="hansen_lossyear":
                spec=gfw_layer(gfw,"umd_tree_cover_loss",None,None,"high")
                return {
                    **spec,
                    "requested_layer_id":layer_id,
                    "fallback_used":True,
                    "fallback_reason":str(primary_error),
                    "fallback_semantics":"Hansen/GFW tree-cover loss history.",
                    "source":"Global Forest Watch / Hansen",
                }
            if layer_id=="modis_burned_area":
                spec=gfw_layer(gfw,"umd_tree_cover_loss_from_fires",None,None,"high")
                return {
                    **spec,
                    "requested_layer_id":layer_id,
                    "fallback_used":True,
                    "fallback_reason":str(primary_error),
                    "fallback_semantics":"Fire-related tree-cover loss history; not MODIS MCD64A1 BurnDate.",
                    "source":"Global Forest Watch fire-related tree-cover loss",
                }
            if layer_id=="modis_lst":
                spec=gibs.tile_spec("modis_terra_lst_day",fallback_date)
                return {
                    **spec,
                    "requested_layer_id":layer_id,
                    "fallback_used":True,
                    "fallback_reason":str(primary_error),
                    "fallback_semantics":"NASA GIBS MODIS Terra daytime land-surface temperature.",
                }
            if layer_id=="chirps_rainfall":
                spec=gibs.tile_spec("imerg_precipitation_rate",fallback_date)
                return {
                    **spec,
                    "requested_layer_id":layer_id,
                    "fallback_used":True,
                    "fallback_reason":str(primary_error),
                    "fallback_semantics":"NASA GPM IMERG precipitation-rate visualization; not CHIRPS.",
                }
            if layer_id=="jrc_water_occurrence":
                spec=gibs.tile_spec("opera_surface_water_hls",fallback_date)
                return {
                    **spec,
                    "requested_layer_id":layer_id,
                    "fallback_used":True,
                    "fallback_reason":str(primary_error),
                    "fallback_semantics":"NASA OPERA dynamic surface water; not long-term JRC occurrence frequency.",
                }
        except Exception as fallback_error:
            raise HTTPException(
                503,
                f"{primary_error}; credential-free fallback also failed: {fallback_error}",
            )
        raise HTTPException(503, str(primary_error))


@app.get("/api/earth-engine/value/{layer_id}")
def earth_engine_value(layer_id: str, lat: float, lon: float, days: int = Query(3650, ge=1, le=3650)):
    try:
        return ee.sample(layer_id, lat, lon, days)
    except AdapterError as e:
        raise HTTPException(503, str(e))


@app.get("/api/bhuvan/info")
def bhuvan_info():
    return {
        "source": "ISRO/NRSC Bhuvan", "wms_url": settings.bhuvan_wms_url, "version": "1.1.1",
        "tile_template": "/api/bhuvan/tile/{z}/{x}/{y}.png?layer=<BhuvanLayerName>",
        "note": "Use layer names published by the Bhuvan thematic services catalogue. The proxy validates the layer name and preserves Bhuvan as the source.",
    }


@app.get("/api/bhuvan/tile/{z}/{x}/{y}.png")
async def bhuvan_tile(z: int, x: int, y: int, layer: str):
    try:
        data, ctype = await bhuvan.tile(z, x, y, layer)
        return Response(content=data, media_type=ctype, headers={"Cache-Control":"public, max-age=3600"})
    except AdapterError as e:
        raise HTTPException(502, str(e))


@app.get("/api/mosdac/info")
def mosdac_info():
    return {
        "source": "ISRO/SAC MOSDAC", "catalog": mosdac.catalog_url, "manual": mosdac.manual_url,
        "official_client": mosdac.client_url, "search_requires_login": False, "download_requires_login": True,
        "max_count_per_search": 100, "daily_download_file_limit": 5000,
        "note": "VanRakshak generates the official mdapi config safely; credentials are never committed to Git.",
    }


@app.get("/api/mosdac/config")
def mosdac_config(dataset_id: str, start: str = "", end: str = "", count: int = Query(50, ge=1, le=100), bbox: str = ""):
    try:
        return mosdac.config(dataset_id, start, end, count, bbox)
    except AdapterError as e:
        raise HTTPException(422, str(e))


@app.get("/api/ai/change-model/status")
def change_model_status_ep():
    return change_model_status()


@app.get("/api/soil", response_model=SourceResult)
async def soil_ep(lat: float, lon: float):
    return await wrap("SoilGrids", soil.point(lat, lon), "REFERENCE", soil.source_url, 250)


@app.get("/api/human-pressure", response_model=SourceResult)
async def pressure_ep(lat: float, lon: float, radius_m: int = Query(5000, ge=500, le=25000)):
    result = await wrap("OpenStreetMap / Overpass", overpass.pressure(lat, lon, radius_m), "DYNAMIC_RECENT", overpass.source_url)
    if result.ok and isinstance(result.data, dict):
        els = result.data.get("elements", [])
        result.data = {"count": len(els), "elements": els[:250], "radius_m": radius_m}
    return result


@app.get("/api/fire", response_model=SourceResult)
async def fire_ep(lat: float, lon: float, days: int = Query(1, ge=1, le=5)):
    return await fire_source_result(lat, lon, days)


@app.get("/api/fire/intelligence")
async def fire_intelligence(lat: float, lon: float, days: int = Query(1, ge=1, le=5)):
    fire = await fire_source_result(lat, lon, days)
    weather_result = await weather_source_result(lat,lon)
    cur = (weather_result.data or {}).get("current", {}) if weather_result.ok and isinstance(weather_result.data, dict) else {}
    count = len(fire.data or []) if fire.ok and isinstance(fire.data, list) else 0
    humidity = cur.get("relative_humidity_2m")
    wind = cur.get("wind_speed_10m")
    rain = cur.get("rain")
    score = 0.0
    score += min(45.0, count * 8.0)
    if humidity is not None: score += max(0.0, min(20.0, (45-float(humidity))*0.7))
    if wind is not None: score += min(20.0, float(wind)*0.6)
    if rain is not None and float(rain) == 0: score += 10.0
    score = round(min(100.0, score), 1)
    level = "LOW" if score < 25 else "MODERATE" if score < 50 else "HIGH" if score < 75 else "VERY_HIGH"
    return {
        "fire": fire.model_dump(),
        "weather": weather_result.model_dump(),
        "wind_direction_deg": cur.get("wind_direction_10m"),
        "wind_speed_kmh": wind,
        "context_score": score,
        "context_level": level,
        "label": "AI_ESTIMATE",
        "warning": "This is a situational fire-weather context score, not a physical fire-spread forecast.",
    }


@app.get("/api/fire/history")
def fire_history(limit: int = Query(200, ge=1, le=2000)):
    try:
        from app.db import SessionLocal, FireObservationRecord
        with SessionLocal() as db:
            rows=db.query(FireObservationRecord).order_by(FireObservationRecord.ingested_at.desc()).limit(limit).all()
            return {
                "count":len(rows),
                "observations":[{
                    "id":r.id,"ingested_at":r.ingested_at.isoformat() if r.ingested_at else None,
                    "source":r.source,"observed_at":r.observed_at,"lat":r.lat,"lon":r.lon,
                    "frp":r.frp,"confidence":r.confidence,"payload":r.payload,
                } for r in rows],
                "source":"VanRakshak scheduled fire observation store",
            }
    except Exception as exc:
        raise HTTPException(503, f"Fire history persistence unavailable: {exc}")


@app.get("/api/eonet/events")
async def eonet_events(lat: float, lon: float, days: int = Query(30, ge=1, le=365), radius_deg: float = Query(3, ge=.2, le=20)):
    return await wrap("NASA EONET", eonet.events(lat, lon, days=days, radius_deg=radius_deg), "DYNAMIC_RECENT", eonet.source_url)


@app.get("/api/gibs/catalog")
def gibs_catalog():
    return {"layers": gibs.catalog(), "auth_required": False, "source": gibs.source_url}


@app.get("/api/gibs/layer/{layer_id}")
def gibs_layer(layer_id: str, date: str | None = None):
    try:
        return gibs.tile_spec(layer_id, date)
    except AdapterError as exc:
        raise HTTPException(422, str(exc))


@app.get("/api/fallbacks/status")
def fallback_status():
    return {
        "strategy": provider_strategy(),
        "credentials": {
            "firms": bool(settings.firms_map_key),
            "protected_planet": bool(settings.protected_planet_token),
            "earth_engine": bool(settings.google_cloud_project),
        },
        "rule": "A credential-gated source may improve precision/coverage, but the dashboard remains operational through public fallbacks where a scientifically valid substitute exists.",
    }


@app.get("/api/protected-areas", response_model=SourceResult)
async def protected_ep(page: int = 1):
    return await wrap("Protected Planet API v4", pp.india(page), "REFERENCE", pp.source_url)


@app.get("/api/protected-areas/{site_id}", response_model=SourceResult)
async def protected_site(site_id: str, with_geometry: bool = True):
    return await wrap("Protected Planet API v4", pp.site(site_id, with_geometry), "REFERENCE", pp.source_url)


@app.get("/api/protected-areas/{site_id}/parcels", response_model=SourceResult)
async def protected_parcels(site_id: str, with_geometry: bool = True):
    return await wrap("Protected Planet API v4 parcels", pp.parcels(site_id, with_geometry), "REFERENCE", pp.source_url)


@app.get("/api/protected-area/context", response_model=SourceResult)
async def protected_context_ep(lat: float, lon: float):
    return await protected_source_result(lat, lon)


@app.get("/api/news", response_model=SourceResult)
async def news_ep(place: str = Query(..., min_length=2), timespan: str = "1week"):
    return await news_source_result(place,timespan)


@app.get("/api/gfw", response_model=SourceResult)
async def gfw_ep():
    return await wrap("Global Forest Watch", gfw.metadata(), "DYNAMIC_RECENT", gfw.source_url)


@app.get("/api/investigate")
async def investigate(lat: float, lon: float, place: str = "India"):
    sources = await investigation_sources(lat, lon, place)
    return {
        "location": {"lat": lat, "lon": lon, "place": place}, "sources": sources,
        "classification_note": "Observed, derived, forecast and AI-estimated data remain visually separated. Probable drivers are not legal proof of causation.",
    }


@app.get("/api/forest-profile")
async def forest_profile(lat: float, lon: float, place: str = "India"):
    sources = await investigation_sources(lat, lon, place)
    location = sources.get("reverse_geocode", {}).get("data") or {}
    address = location.get("address", {}) if isinstance(location, dict) else {}
    weather_full = sources.get("weather", {}).get("data") or {}
    weather_data = weather_full.get("current", {})
    pressure = sources.get("human_pressure", {}).get("data") or {}
    fires = sources.get("fire", {}).get("data") or []
    earth_data = sources.get("earth_search", {}).get("data") or {}
    scenes = earth_data.get("features", []) if isinstance(earth_data, dict) else []
    ee_values = {}
    if settings.google_cloud_project:
        for lid in ("dynamic_world_trees","srtm_elevation","srtm_slope","srtm_aspect","gedi_agbd","wcmc_carbon_density","worldpop_population","human_modification","wdpa_protected"):
            try:
                ee_values[lid] = await asyncio.to_thread(ee.sample, lid, lat, lon, 3650)
            except Exception as exc:
                ee_values[lid] = {"error": str(exc)}
    return {
        "location": {
            "lat": lat, "lon": lon, "display_name": location.get("display_name") if isinstance(location, dict) else place,
            "state": address.get("state"), "district": address.get("state_district") or address.get("county"),
        },
        "satellite": {
            "available_scenes": len(scenes),
            "latest_scene_time": ((scenes[0].get("properties") or {}).get("datetime") if scenes else None),
            "resolution_m": 10,
        },
        "environment": {
            "temperature_c": weather_data.get("temperature_2m"), "humidity_pct": weather_data.get("relative_humidity_2m"),
            "rain_mm": weather_data.get("rain"), "cloud_cover_pct": weather_data.get("cloud_cover"),
            "wind_kmh": weather_data.get("wind_speed_10m"),
        },
        "human_pressure": {
            "mapped_features": pressure.get("count") if isinstance(pressure, dict) else None,
            "human_modification_reference": (ee_values.get("human_modification") or {}).get("value"),
            "population_reference": (ee_values.get("worldpop_population") or {}).get("value"),
        },
        "fire": {
            "detections_in_window": len(fires) if isinstance(fires, list) else None,
            "configured": sources.get("fire", {}).get("ok", False),
            "source": (sources.get("fire", {}).get("provenance") or {}).get("source"),
        },
        "forest": {
            "dynamic_world_tree_probability": (ee_values.get("dynamic_world_trees") or {}).get("value"),
            "gedi_agbd_mg_per_ha": (ee_values.get("gedi_agbd") or {}).get("value"),
            "carbon_density_t_per_ha_reference": (ee_values.get("wcmc_carbon_density") or {}).get("value"),
        },
        "terrain": {
            "elevation_m": (ee_values.get("srtm_elevation") or {}).get("value") if ee_values.get("srtm_elevation") else weather_full.get("elevation"),
            "slope_deg": (ee_values.get("srtm_slope") or {}).get("value"),
            "aspect_deg": (ee_values.get("srtm_aspect") or {}).get("value"),
        },
        "conservation": (sources.get("protected_area") or {}).get("data") or ee_values.get("wdpa_protected"),
        "soil": sources.get("soil"),
        "earth_engine": {"configured": bool(settings.google_cloud_project), "values": ee_values},
        "provenance": {k: v.get("provenance") for k, v in sources.items()},
        "raw_sources": sources,
        "note": "Credential-free fallbacks keep satellite, fire context, protected-area context, geocoding, weather and public forest layers operational. Earth Engine still adds higher-value canopy/terrain/biomass/carbon/population layers when authenticated; absent values are never fabricated.",
    }


@app.post("/api/investigations/persist")
def persist_investigation(req: PersistInvestigationRequest):
    try:
        from app.db import SessionLocal, InvestigationRecord
        with SessionLocal() as db:
            rec = InvestigationRecord(lat=req.lat, lon=req.lon, place=req.place, payload=req.payload)
            db.add(rec); db.commit(); db.refresh(rec)
            return {"id": rec.id, "stored": True}
    except Exception as e:
        raise HTTPException(503, f"Persistence unavailable: {e}")


@app.post("/api/intelligence/risk")
def risk_ep(x: RiskInputs): return risk_score(x)

@app.post("/api/intelligence/cascade")
def cascade_ep(x: RiskInputs): return cascade(x)

@app.post("/api/intelligence/resilience")
def resilience_ep(x: RiskInputs): return resilience(x)

@app.post("/api/intelligence/intervention")
def intervention_ep(x: RiskInputs): return {"recommendations": intervention(x), "label": "AI_ESTIMATE"}

@app.post("/api/intelligence/what-if")
def what_if(req: WhatIfRequest):
    b = req.base.model_copy(deep=True)
    b.temp_anomaly_c = max(0, min(10, b.temp_anomaly_c + req.temperature_delta_c))
    b.rainfall_deficit_pct = max(0, min(100, b.rainfall_deficit_pct + req.rainfall_delta_pct))
    b.fire_signal = max(0, min(1, b.fire_signal + req.fire_delta))
    b.ndvi_drop = max(0, min(1, b.ndvi_drop + req.ndvi_delta))
    return {"baseline": risk_score(req.base), "scenario": risk_score(b), "scenario_inputs": b.model_dump(), "label": "AI_ESTIMATE"}

@app.post("/api/intelligence/predict")
def prediction_ep(req: ThreatPredictionRequest):
    try: return predict_threat(req)
    except ValueError as e: raise HTTPException(422, str(e))

@app.get("/api/intelligence/predict-location")
async def predict_location_ep(
    lat: float, lon: float, start: str, end: str, max_observations: int = Query(10, ge=3, le=16), cloud_lt: float = Query(50, ge=0, le=100),
):
    series=await vegetation_series_ep(lat,lon,start,end,max_observations,cloud_lt,1.5)
    rows=series["observations"]
    valid=[x for x in rows if x.get("mean_ndvi") is not None and x.get("forest_fraction") is not None]
    if len(valid)<3:
        raise HTTPException(422,"At least three valid satellite observations are required")
    valid=sorted(valid,key=lambda x:x.get("datetime") or "")
    n=min(3,max(2,len(valid)//3))
    base_nd=sum(float(x["mean_ndvi"]) for x in valid[:n])/n
    base_fc=sum(float(x["forest_fraction"]) for x in valid[:n])/n
    risk_values=[]; components=[]
    for x in valid:
        nd=max(0,min(1,(base_nd-float(x["mean_ndvi"]))/0.4))
        fc=max(0,min(1,(base_fc-float(x["forest_fraction"]))/0.30))
        risk=round((nd*.55+fc*.45)*100,2)
        risk_values.append(risk)
        components.append({"date":(x.get("datetime") or "")[:10],"risk_index":risk,"ndvi_decline_component":round(nd*100,1),"forest_fraction_decline_component":round(fc*100,1),"mean_ndvi":x.get("mean_ndvi"),"forest_fraction":x.get("forest_fraction"),"cloud_masked_fraction":x.get("cloud_masked_fraction"),"scene_id":x.get("id") or x.get("scene")})
    dates=[x["date"] for x in components]
    projection=predict_threat(ThreatPredictionRequest(values=risk_values,dates=dates,steps=4,floor=0,ceiling=100))
    first,last=valid[0],valid[-1]
    ndvi_change=round(float(last["mean_ndvi"])-float(first["mean_ndvi"]),4)
    forest_change=round(float(last["forest_fraction"])-float(first["forest_fraction"]),4)
    cloud_values=[float(x.get("cloud_masked_fraction")) for x in valid if x.get("cloud_masked_fraction") is not None]
    quality=max(0.0,min(100.0,100.0-(sum(cloud_values)/len(cloud_values)*100 if cloud_values else 0.0)))
    p=projection.get("analysis") or {}
    interpretation="Observed vegetation/forest decline is producing a rising screening-risk trend." if p.get("direction")=="INCREASING" else "The derived screening-risk trend is easing over the selected observation period." if p.get("direction")=="DECREASING" else "The derived screening-risk trend is broadly stable over the selected observation period."
    return {"location":{"lat":lat,"lon":lon},"period":{"start":start,"end":end},"historical_risk_proxy":risk_values,"dates":dates,"projection":projection,"analysis":{"interpretation":interpretation,"ndvi_change_first_to_latest":ndvi_change,"forest_fraction_change_first_to_latest":forest_change,"latest_observation":dates[-1],"observation_count":len(valid),"scene_read_errors":len(series.get("errors") or []),"optical_quality_pct":round(quality,1),"baseline_mean_ndvi":round(base_nd,4),"baseline_forest_fraction":round(base_fc,4),"current_risk_index":risk_values[-1],"projected_risk_index":(projection.get("projected_values") or [None])[-1],"model_confidence_pct":p.get("confidence_pct")},"components":components,"source_series":valid,"source":series.get("source"),"pipeline":["Search real Sentinel-2 L2A scenes in the selected period","Read red/NIR pixels and mask cloud/shadow/snow using SCL","Compute mean NDVI and forest fraction for each observation","Convert decline from the early-period baseline into a 0-100 screening-risk index","Run robust ensemble trend forecasting and uncertainty analysis"],"generated_at":datetime.now(timezone.utc).isoformat(),"label":"AI_ESTIMATE","warning":"Risk index is a transparent screening indicator derived from optical vegetation/forest-fraction decline. It is not a probability of illegal deforestation and should be checked against seasonality, radar and field evidence."}


@app.post("/api/intelligence/forest-doctor")
def forest_doctor_ep(x: ForestDoctorInputs): return forest_doctor(x)

@app.post("/api/intelligence/recovery")
def recovery_ep(x: RecoveryInputs): return recovery(x)

@app.post("/api/intelligence/correlation")
def correlation_ep(x: CorrelationInputs):
    try: return correlations(x)
    except ValueError as e: raise HTTPException(422, str(e))

@app.post("/api/intelligence/compare-regions")
def compare_ep(x: RegionComparisonRequest): return compare_regions(x)

@app.post("/api/intelligence/anomaly-radar")
def anomaly_ep(signals: dict[str, float]): return anomaly_radar(signals)


@app.post("/api/analysis/ndvi-change")
async def ndvi_change_ep(before: UploadFile = File(...), after: UploadFile = File(...), threshold: float = Query(.2, ge=.01, le=1)):
    try: return ndvi_change(await before.read(), await after.read(), threshold)
    except RasterInputError as e: raise HTTPException(422, str(e))


@app.get("/api/analysis/remote-change")
async def remote_change_ep(
    lat: float, lon: float, before_date: str, after_date: str,
    radius_km: float = Query(2.0, ge=.2, le=10), ndvi_drop_threshold: float = Query(.2, ge=.05, le=.8),
    forest_ndvi_threshold: float = Query(.45, ge=0, le=.9), cloud_lt: float = Query(60, ge=0, le=100),
):
    try:
        bdate=datetime.fromisoformat(before_date).replace(tzinfo=timezone.utc)
        adate=datetime.fromisoformat(after_date).replace(tzinfo=timezone.utc)
    except Exception:
        raise HTTPException(422,"Dates must use YYYY-MM-DD")
    key=f"remote-change:{round(lat,5)}:{round(lon,5)}:{before_date}:{after_date}:{radius_km}:{ndvi_drop_threshold}:{forest_ndvi_threshold}:{cloud_lt}"
    async def produce():
        before=await earth.closest_scene(lat,lon,bdate,35,cloud_lt)
        after=await earth.closest_scene(lat,lon,adate,35,cloud_lt)
        if not before or not after:
            raise HTTPException(404,"Could not find suitable Sentinel-2 scenes for both dates")
        try:
            return await asyncio.to_thread(remote_change_analyze,before,after,lat,lon,radius_km,ndvi_drop_threshold,forest_ndvi_threshold)
        except Exception as e:
            raise HTTPException(503,f"Remote Sentinel analysis failed: {e}")
    return await cached_async(key,max(settings.cache_ttl_s,86400),produce)


@app.get("/api/analysis/sar-change")
async def sar_change_ep(
    lat: float, lon: float, before_date: str, after_date: str,
    radius_km: float = Query(2.0, ge=.2, le=8),
    window_days: int = Query(24, ge=7, le=60),
    drop_db_threshold: float = Query(2.5, ge=.5, le=10),
):
    try:
        bdate=datetime.fromisoformat(before_date).replace(tzinfo=timezone.utc)
        adate=datetime.fromisoformat(after_date).replace(tzinfo=timezone.utc)
    except Exception:
        raise HTTPException(422,"Dates must use YYYY-MM-DD")
    key=f"sar-change:{round(lat,5)}:{round(lon,5)}:{before_date}:{after_date}:{radius_km}:{window_days}:{drop_db_threshold}"
    async def produce():
        pair=await earth.closest_sentinel1_pair(lat,lon,bdate,adate,window_days)
        if not pair:
            raise HTTPException(404,"Could not find a matched-orbit Sentinel-1 pair around both dates")
        before,after=pair
        try:
            return await asyncio.to_thread(sar_change_analyze,before,after,lat,lon,radius_km,drop_db_threshold)
        except Exception as e:
            raise HTTPException(503,f"Sentinel-1 SAR change screening failed: {e}")
    return await cached_async(key,max(settings.cache_ttl_s,86400),produce)


@app.get("/api/analysis/evidence-chain")
async def evidence_chain_ep(
    lat: float, lon: float, place: str = "India", before_date: str | None = None, after_date: str | None = None,
    radius_km: float = Query(2.0, ge=.2, le=10), cloud_lt: float = Query(60, ge=0, le=100),
):
    sources = await investigation_sources(lat, lon, place)
    climate = None
    try:
        climate = await climate_anomaly_real(lat, lon, 30, 5)
    except Exception:
        climate = None
    change = None
    sar_change = None
    if before_date and after_date:
        try:
            change=await remote_change_ep(lat,lon,before_date,after_date,radius_km,.2,.45,cloud_lt)
        except Exception:
            change=None
        try:
            sar_change=await sar_change_ep(lat,lon,before_date,after_date,min(radius_km,8),24,2.5)
        except Exception:
            sar_change=None
    protected_ctx = (sources.get("protected_area") or {}).get("data") or {}
    protected = protected_ctx.get("inside") if isinstance(protected_ctx, dict) and "inside" in protected_ctx else None
    carbon=None
    if settings.google_cloud_project:
        try:
            pa=await asyncio.to_thread(ee.sample,"wdpa_protected",lat,lon,3650)
            protected=bool(pa.get("inside_protected_area")); sources["protected_area_ee"]={"ok":True,"data":pa,"provenance":prov("UNEP-WCMC WDPA / Earth Engine","REFERENCE",ee.source_url).model_dump(),"error":None}
        except Exception as exc:
            sources["protected_area_ee"]={"ok":False,"data":None,"provenance":prov("UNEP-WCMC WDPA / Earth Engine","REFERENCE",ee.source_url).model_dump(),"error":str(exc)}
        if change and change.get("candidate_area_ha") is not None:
            try:
                cd=await asyncio.to_thread(ee.sample,"wcmc_carbon_density",lat,lon,3650)
                density=cd.get("value")
                if density is not None:
                    tc=float(change["candidate_area_ha"])*float(density)
                    carbon={"reference_carbon_density_tC_per_ha":density,"estimated_carbon_loss_tC":round(tc,2),"estimated_co2e_t":round(tc*44/12,2),"uncertainty_note":"Reference carbon-density layer circa 2010; this is an order-of-magnitude impact estimate, not a field inventory.","label":"AI_ESTIMATE"}
            except Exception:
                carbon=None
    if carbon is None and change and change.get("candidate_area_ha") is not None:
        # Credential-free scientific fallback: broad IPCC Tier-1 reference for
        # continental Asian tropical moist forest. It is intentionally labelled
        # as a reference-based estimate, never as a local biomass measurement.
        try:
            ref = carbon_estimate(CarbonRequest(
                area_ha=max(0.001, float(change["candidate_area_ha"])),
                biomass_t_per_ha=182.0,
                uncertainty_pct=75.0,
            ))
            carbon={
                **ref,
                "reference_biomass_density_t_dry_matter_per_ha":182.0,
                "density_source":"IPCC Good Practice Guidance for LULUCF, Table 3A.1.2 — continental Asia tropical moist forest (short dry season)",
                "source_url":"https://www.ipcc-nggip.iges.or.jp/public/gpglulucf/gpglulucf_files/Chp3/Anx_3A_1_Data_Tables.pdf",
                "estimate_class":"BROAD_REFERENCE_FALLBACK",
                "warning":"Broad Tier-1 reference estimate, not a site-specific GEDI/field biomass measurement. Replace automatically when a location-specific carbon-density provider is configured.",
            }
        except Exception:
            carbon=None

    if sar_change:
        sources["sar_change"]={
            "ok":True,
            "data":sar_change,
            "provenance":prov("Sentinel-1 GRD / Earth Search","DYNAMIC_RECENT",earth.source_url,observed_at=(sar_change.get("after") or {}).get("datetime"),notes=sar_change.get("warning")).model_dump(),
            "error":None,
        }
    chain=build_chain(sources,change,climate)
    warning=partial_risk(change,sources,climate,protected)
    doctor=None
    pctx=pressure_context(sources.get("human_pressure") or {},lat,lon)
    if change:
        fire=sources.get("fire") or {}
        fire_source=((fire.get("provenance") or {}).get("source") or "")
        raw_fire_signal=min(1,len(fire.get("data") or [])/10) if fire.get("ok") else 0
        # EONET is contextual event evidence, not pixel-level thermal detection.
        fire_signal=min(.2, raw_fire_signal) if "EONET" in fire_source else raw_fire_signal
        drought=min(1,max(0,(climate or {}).get("rainfall_deficit_pct") or 0)/70)
        frag=change.get("fragmentation") or {}; fchg=frag.get("change") or {}
        radar_available=((sources.get("sentinel1") or {}).get("ok") is True)
        radar_change_signal=min(1.0,max(0.0,(sar_change or {}).get("candidate_fraction") or 0.0)*5.0)
        doctor=forest_doctor(ForestDoctorInputs(
            ndvi_drop=min(1,max(0,-(change.get("mean_ndvi_change") or 0))),
            fire_signal=fire_signal, drought_severity=drought,
            road_proximity_km=pctx.get("nearest_road_km"), settlement_proximity_km=pctx.get("nearest_settlement_km"),
            mining_or_quarry_nearby=pctx.get("mining_or_quarry_nearby",False),
            landcover_to_crop=0, radar_change=radar_change_signal,
        ))
        doctor["availability_note"]="Measured Sentinel-1 SAR change is used only when a matched-orbit pair can be read. Scene availability alone is never treated as radar confirmation."
        doctor["human_pressure_context"]=pctx
        doctor["radar_scene_available"]=radar_available
        doctor["fragmentation_change"]=fchg
    bundle={"location":{"lat":lat,"lon":lon,"place":place},"change":change,"sar_change":sar_change,"climate":climate,"carbon":carbon,"protected_area":protected,"evidence_chain":chain,"warning":warning,"forest_doctor":doctor,"sources":sources}
    live_inputs=_live_risk_inputs(bundle,lat,lon)
    bundle["action_plan"]=_action_plan_from_evidence(bundle,live_inputs,lat,lon)
    return bundle



def _clamp01(value):
    try:
        return max(0.0,min(1.0,float(value)))
    except Exception:
        return 0.0


def _live_risk_inputs(bundle: dict, lat: float, lon: float) -> RiskInputs:
    change=bundle.get("change") or {}
    climate=bundle.get("climate") or {}
    sources=bundle.get("sources") or {}
    sar=bundle.get("sar_change") or {}
    protected=bool(bundle.get("protected_area")) if bundle.get("protected_area") is not None else False

    ndvi_drop=_clamp01(max(0.0,-float(change.get("mean_ndvi_change") or 0.0)))
    temp=max(0.0,float(climate.get("temperature_anomaly_c") or 0.0))
    rain=max(0.0,float(climate.get("rainfall_deficit_pct") or 0.0))

    fire=sources.get("fire") or {}
    fire_source=((fire.get("provenance") or {}).get("source") or "")
    rows=fire.get("data") or []
    fire_signal=_clamp01(len(rows)/10.0) if fire.get("ok") else 0.0
    if "EONET" in fire_source:
        fire_signal=min(0.2,fire_signal)

    frag=(change.get("fragmentation") or {})
    fchg=frag.get("change") or {}
    fbefore=frag.get("before") or {}
    edge_delta=max(0.0,float(fchg.get("edge_pixel_fraction_delta") or 0.0))
    patch_delta=max(0.0,float(fchg.get("patch_count_delta") or 0.0))
    patch_base=max(1.0,float(fbefore.get("patch_count") or 1.0))
    frag_signal=_clamp01(edge_delta*4.0 + (patch_delta/patch_base))

    pctx=pressure_context(sources.get("human_pressure") or {},lat,lon)
    counts=pctx.get("counts") or {}
    pressure_count=sum(float(v or 0) for v in counts.values())
    human_pressure=_clamp01(pressure_count/80.0)

    confidence=max(
        float(change.get("screening_confidence") or 0.0),
        float(sar.get("screening_confidence") or 0.0),
    )
    if confidence<=0:
        confidence=0.0

    return RiskInputs(
        ndvi_drop=ndvi_drop,
        temp_anomaly_c=min(10.0,temp),
        rainfall_deficit_pct=min(100.0,rain),
        fire_signal=fire_signal,
        protected_area=protected,
        fragmentation_change=frag_signal,
        human_pressure=human_pressure,
        model_confidence=_clamp01(confidence),
    )


def _action_plan_from_evidence(bundle: dict, inputs: RiskInputs, lat: float, lon: float) -> dict:
    """Build an operational, evidence-linked response plan without inventing outcomes."""
    risk=risk_score(inputs)
    change=bundle.get("change") or {}
    sources=bundle.get("sources") or {}
    pctx=pressure_context(sources.get("human_pressure") or {},lat,lon)
    location=bundle.get("location") or {}
    place=location.get("place") or "selected area"
    candidate_area=float(change.get("candidate_area_ha") or 0.0)
    center=_geojson_centroid(change.get("geojson") or {}) if change.get("geojson") else None
    if center:
        change_where=f"Detected change footprint near {center[0]:.5f}, {center[1]:.5f} within {place}"
    else:
        change_where=f"Selected AOI around {lat:.5f}, {lon:.5f} ({place})"

    actions=[]
    def add(priority,what,where,how,timeframe,why,expected_impact,success_metric):
        actions.append({
            "priority":priority,
            "what":what,
            "where":where,
            "how":how,
            "timeframe":timeframe,
            "why":why,
            "expected_impact":expected_impact,
            "success_metric":success_metric,
        })

    if candidate_area>0 or inputs.ndvi_drop>=0.08:
        area_label=f"{candidate_area:.2f} ha" if candidate_area>0 else "the detected vegetation-change footprint"
        add(
            "URGENT" if (risk.get("score") or 0)>=50 else "HIGH",
            "Ground-verify the detected vegetation change",
            change_where,
            "Open Before/After, inspect the evidence chain, generate the incident report, then route the patrol team to the candidate polygon and capture geotagged field evidence.",
            "Within 24 hours",
            "Satellite screening indicates vegetation loss/stress that needs field confirmation before enforcement or remediation decisions.",
            f"Confirm or reject the current {area_label} satellite signal and create a defensible ground-truth record.",
            f"Field verification completed; on the next suitable satellite scene the candidate footprint should not expand beyond the current {area_label} if the disturbance has stopped.",
        )

    if inputs.fire_signal>0.20:
        fire_rows=(sources.get("fire") or {}).get("data") or []
        add(
            "URGENT",
            "Verify active fire / heat signals and prepare rapid response",
            f"Fire-context points in and around the selected AOI ({lat:.5f}, {lon:.5f})",
            "Open Fire & Heat, confirm the source type, attach the highest-priority points to the patrol route, notify the patrol/fire team, and re-check wind, humidity and rain before dispatch.",
            "Immediately / next patrol cycle",
            f"Fire intelligence is contributing to the current warning model ({len(fire_rows)} returned context points).",
            "Earlier confirmation of a real thermal event and faster field escalation when a fire is present.",
            "After response, target zero new verified thermal detections in the AOI and no increase in burn/change indicators on the next observation.",
        )

    if inputs.human_pressure>=0.25 or pctx.get("nearest_road_km") is not None or pctx.get("nearest_settlement_km") is not None:
        proximity=[]
        if pctx.get("nearest_road_km") is not None: proximity.append(f"road {pctx['nearest_road_km']:.2f} km")
        if pctx.get("nearest_settlement_km") is not None: proximity.append(f"settlement {pctx['nearest_settlement_km']:.2f} km")
        add(
            "HIGH",
            "Prioritize access-route and settlement-edge patrol checks",
            change_where + (f" • nearest mapped {'; '.join(proximity)}" if proximity else ""),
            "Use the Patrol Optimizer to visit detected-change centroids first, then mapped road/quarry/settlement access points. Record whether clearing, vehicles, extraction or boundary breaches are actually present.",
            "Within 24–48 hours",
            "Mapped human-pressure features increase the value of targeted field verification, but OSM completeness varies.",
            "Concentrates patrol time on the most plausible access routes instead of uniform coverage.",
            "All top-priority access points visited and documented; repeat alerts should not move outward from the currently detected footprint.",
        )

    if inputs.protected_area:
        add(
            "URGENT",
            "Escalate the incident through the protected-area workflow",
            change_where,
            "Attach the evidence-chain report, coordinates, before/after imagery and patrol route to the responsible forest/protected-area officer. Preserve timestamps and source links.",
            "Same day",
            "The selected location is reported inside protected-area context, increasing conservation sensitivity.",
            "Faster evidence handoff and a clearer chain of custody for the responsible authority.",
            "Incident package acknowledged by the responsible team with location, imagery, evidence sources and assigned field action.",
        )

    if inputs.rainfall_deficit_pct>=25 or inputs.temp_anomaly_c>=1.5:
        add(
            "MEDIUM",
            "Separate climate stress from direct clearing before final classification",
            f"Selected AOI and surrounding vegetation buffer near {lat:.5f}, {lon:.5f}",
            "Review temperature/rainfall anomaly, soil moisture and evapotranspiration together with NDVI. Re-check on the next cloud-free observation before labelling climate-driven browning as clearing.",
            "Re-check within 3–7 days",
            "Heat or rainfall-deficit signals can reduce vegetation indices without direct tree removal.",
            "Reduces avoidable false escalation and improves the interpretation of vegetation stress.",
            "NDVI, rainfall and soil-moisture direction are re-evaluated together; classification is updated only when the evidence agrees.",
        )

    if inputs.fragmentation_change>=0.15:
        add(
            "HIGH",
            "Protect corridor and forest-edge connectivity around the disturbance",
            change_where,
            "Inspect new edges/patch breaks on the change layer, prioritize narrow connectors and core-forest boundaries in the patrol route, and mark the same geometry for follow-up comparison.",
            "Within 48 hours",
            "Fragmentation can create lasting ecological impact even when total affected area is modest.",
            "Focuses intervention on preventing further edge expansion and isolation of forest patches.",
            "Next comparison shows no worsening in patch/edge fragmentation metrics around the same geometry.",
        )

    add(
        "ROUTINE",
        "Schedule evidence refresh and satellite re-check",
        f"Same selected AOI: {lat:.5f}, {lon:.5f}",
        "Refresh provider health, reload the newest cloud-screened scene, rerun the evidence chain, and compare warning score, NDVI, candidate area, fire context and fragmentation against this baseline.",
        "Next suitable satellite observation",
        "A response is only complete when the next observation verifies whether conditions stabilized, improved or worsened.",
        "Creates a measurable before/after audit trail for the intervention.",
        "No unexplained increase in candidate area or fragmentation; no new verified fire signal; NDVI is stable or improving relative to this baseline.",
    )

    return {
        "label":"AI_ESTIMATE",
        "risk_before":risk,
        "selected_area":{"lat":lat,"lon":lon,"place":place,"candidate_area_ha":round(candidate_area,3)},
        "actions":actions,
        "expected_outcome":"If the recommended response is effective, later observations should show a stable or smaller candidate-change footprint, no new verified fire signal, stable/improving NDVI, and no worsening fragmentation. These are validation targets, not guaranteed impact percentages.",
        "method":"Operational recommendations are triggered only by evidence-derived risk inputs. Expected impacts are expressed as measurable success targets rather than fabricated outcome claims.",
    }


def _geojson_centroid(feature: dict):
    geom=(feature or {}).get("geometry") or {}
    coords=geom.get("coordinates")
    pts=[]
    def walk(x):
        if isinstance(x,(list,tuple)) and len(x)>=2 and all(isinstance(v,(int,float)) for v in x[:2]):
            pts.append((float(x[1]),float(x[0])))
        elif isinstance(x,(list,tuple)):
            for y in x: walk(y)
    walk(coords)
    if not pts: return None
    return (sum(p[0] for p in pts)/len(pts),sum(p[1] for p in pts)/len(pts))


@app.get("/api/intelligence/live")
async def live_intelligence_ep(
    lat: float, lon: float, place: str="India",
    before_date: str | None=None, after_date: str | None=None,
    radius_km: float=Query(2.0,ge=.2,le=8), cloud_lt: float=Query(60,ge=0,le=100),
):
    bundle=await evidence_chain_ep(lat,lon,place,before_date,after_date,radius_km,cloud_lt)
    inputs=_live_risk_inputs(bundle,lat,lon)
    live_risk=risk_score(inputs)
    live_cascade=cascade(inputs)
    live_resilience=resilience(inputs)
    live_interventions=intervention(inputs)
    signals={
        "vegetation_loss":inputs.ndvi_drop,
        "heat":min(1.0,inputs.temp_anomaly_c/5.0),
        "rainfall_deficit":min(1.0,inputs.rainfall_deficit_pct/100.0),
        "fire":inputs.fire_signal,
        "fragmentation":inputs.fragmentation_change,
        "human_pressure":inputs.human_pressure,
    }
    return {
        "location":bundle.get("location"),
        "inputs_from_real_evidence":inputs.model_dump(),
        "risk":live_risk,
        "cascade":live_cascade,
        "resilience":live_resilience,
        "interventions":{"recommendations":live_interventions,"label":"AI_ESTIMATE"},
        "forest_doctor":bundle.get("forest_doctor"),
        "anomaly_radar":anomaly_radar(signals),
        "carbon":bundle.get("carbon"),
        "protected_area":bundle.get("protected_area"),
        "source_coverage":(bundle.get("warning") or {}).get("coverage"),
        "provenance_rule":"All numeric inputs above are derived from provider/reference observations in this response. Missing evidence is not silently fabricated.",
        "evidence_chain":bundle.get("evidence_chain"),
    }


@app.get("/api/intelligence/what-if-location")
async def what_if_location_ep(
    lat: float, lon: float, place: str="India",
    before_date: str | None=None, after_date: str | None=None,
    temperature_delta_c: float=0, rainfall_delta_pct: float=0, fire_delta: float=0, ndvi_delta: float=0,
):
    bundle=await evidence_chain_ep(lat,lon,place,before_date,after_date,2.0,60)
    base=_live_risk_inputs(bundle,lat,lon)
    req=WhatIfRequest(
        base=base,
        temperature_delta_c=temperature_delta_c,
        rainfall_delta_pct=rainfall_delta_pct,
        fire_delta=fire_delta,
        ndvi_delta=ndvi_delta,
    )
    return {
        "base_from_real_evidence":base.model_dump(),
        "simulation":what_if(req),
        "label":"SCENARIO_FROM_REAL_BASELINE",
        "warning":"Scenario deltas are hypothetical; the baseline is derived from current/observed provider evidence.",
    }


@app.get("/api/patrol/live")
async def live_patrol_ep(
    lat: float, lon: float, place: str="India",
    before_date: str | None=None, after_date: str | None=None,
    max_points: int=Query(5,ge=1,le=10),
):
    if not before_date or not after_date:
        raise HTTPException(422,"before_date and after_date are required for real candidate patrol points")
    bundle=await evidence_chain_ep(lat,lon,place,before_date,after_date,2.0,60)
    change=bundle.get("change") or {}
    features=((change.get("geojson") or {}).get("features") or [])
    points=[]; contexts={}
    base_priority=float((bundle.get("warning") or {}).get("score") or 50)
    confidence=float(change.get("screening_confidence") or 0.0)
    ranked_features=sorted(
        features,
        key=lambda feature:float(((feature.get("properties") or {}).get("area_ha") or 0.0)),
        reverse=True,
    )[:max_points]
    max_area=max([float(((feature.get("properties") or {}).get("area_ha") or 0.0)) for feature in ranked_features] or [0.0])
    for i,feature in enumerate(ranked_features):
        center=_geojson_centroid(feature)
        if center is None: continue
        plat,plon=center
        area_ha=float(((feature.get("properties") or {}).get("area_ha") or 0.0))
        area_signal=(area_ha/max_area) if max_area>0 else 0.0
        priority=max(1,min(100,base_priority*.55+confidence*100*.30+area_signal*15))
        pid=f"candidate-{i+1}"
        points.append({"id":pid,"lat":plat,"lon":plon,"priority":priority})
        contexts[pid]={"candidate_polygon":i+1,"area_ha":round(area_ha,4) if area_ha else None,"screening_confidence":round(confidence,3),"warning_score":round(base_priority,1),"centroid":{"lat":round(plat,6),"lon":round(plon,6)}}
    if not points:
        return {
            "ordering":{"route":[],"stop_count":0,"ordering_mode":"NO_TARGETS","method":"No routing performed because the change screen returned no patrol hotspots."},
            "road_route":None,
            "route_summary":{"stops":0,"ordering_mode":"NO_TARGETS"},
            "status":"NO_PATROL_TARGETS",
            "analysis":{"hotspots_used":0,"candidate_polygon_count":len(features),"candidate_area_ha":change.get("candidate_area_ha"),"screening_confidence":change.get("screening_confidence"),"warning_score":base_priority,"before_scene":(change.get("before") or {}).get("id"),"after_scene":(change.get("after") or {}).get("id"),"before_observed_at":(change.get("before") or {}).get("datetime"),"after_observed_at":(change.get("after") or {}).get("datetime")},
            "pipeline":["Run Sentinel-2 before/after multispectral change screening","Inspect candidate-change polygons","No routable patrol hotspots were detected, so road routing was intentionally skipped"],
            "candidate_source":"Sentinel-2 before/after candidate-change polygons",
            "generated_at":datetime.now(timezone.utc).isoformat(),
            "label":"DERIVED_FROM_REAL_DATA",
            "warning":"No candidate-change patrol hotspots were detected for this comparison. This is a valid analysis result, not a routing failure.",
        }
    routed=await patrol_road_route(PatrolRequest(start_lat=lat,start_lon=lon,points=points))
    for stop in (routed.get("ordering") or {}).get("route") or []:
        stop["candidate_context"]=contexts.get(stop.get("id"))
    return {**routed,"analysis":{"hotspots_used":len(points),"candidate_polygon_count":len(features),"candidate_area_ha":change.get("candidate_area_ha"),"screening_confidence":change.get("screening_confidence"),"warning_score":base_priority,"before_scene":(change.get("before") or {}).get("id"),"after_scene":(change.get("after") or {}).get("id"),"before_observed_at":(change.get("before") or {}).get("datetime"),"after_observed_at":(change.get("after") or {}).get("datetime")},"pipeline":["Run Sentinel-2 before/after multispectral change screening","Convert candidate-change polygons into patrol hotspot centroids","Assign evidence-based patrol priorities from warning/confidence signals","Request OSRM road travel-time matrix and order stops by travel cost + priority","Request final OSM road geometry, ETA, route legs and turn guidance"],"candidate_source":"Sentinel-2 before/after candidate-change polygons","generated_at":datetime.now(timezone.utc).isoformat(),"label":"DERIVED_FROM_REAL_DATA","warning":"Routing uses mapped OSM roads/tracks where available. Candidate polygons are screening evidence, not proof of deforestation; field accessibility and safety must be verified."}


@app.get("/api/alerts/compose")
async def compose_alert_ep(
    lat: float, lon: float, place: str="India",
    before_date: str | None=None, after_date: str | None=None,
):
    if not before_date or not after_date:
        raise HTTPException(422,"before_date and after_date are required to compose a source-backed patrol alert")
    bundle=await evidence_chain_ep(lat,lon,place,before_date,after_date,2.0,60)
    digits=str(abs(int(round(lat*100)))+abs(int(round(lon*100)))).zfill(4)[-4:]
    incident_id=f"VR-{datetime.now(timezone.utc).year}-{digits}"
    alert=compose_patrol_alert(bundle,lat,lon,place,incident_id)
    alert["evidence_chain"]=bundle.get("evidence_chain")
    return alert


@app.post("/api/intelligence/compare-live")
async def compare_live_ep(payload: dict):
    rows=payload.get("regions") or []
    if not isinstance(rows,list) or len(rows)<2 or len(rows)>5:
        raise HTTPException(422,"regions must contain 2 to 5 location objects")
    derived=[]
    for i,row in enumerate(rows):
        try:
            lat=float(row["lat"]); lon=float(row["lon"]); name=str(row.get("name") or f"Region {i+1}")
        except Exception:
            raise HTTPException(422,f"Invalid region at index {i}")
        bundle=await evidence_chain_ep(
            lat,lon,name,row.get("before_date"),row.get("after_date"),
            float(row.get("radius_km") or 1.0),60,
        )
        inputs=_live_risk_inputs(bundle,lat,lon)
        risk=risk_score(inputs)
        change=bundle.get("change") or {}
        fire=((bundle.get("sources") or {}).get("fire") or {})
        derived.append({
            "name":name,
            "risk":float(risk.get("score") or 0),
            "forest_loss_ha":max(0,float(change.get("candidate_area_ha") or 0)),
            "fire_count":len(fire.get("data") or []) if fire.get("ok") else 0,
            "ndvi_drop":inputs.ndvi_drop,
            "protected_area":inputs.protected_area,
        })
    result=compare_regions(RegionComparisonRequest(regions=derived))
    result["source"]="live evidence-chain outputs for each supplied region"
    result["warning"]="Comparison prioritizes measured/derived signals; it is not a legal or causal determination."
    return result


@app.get("/api/query/live")
async def live_query_ep(
    q: str=Query(...,min_length=3), lat: float=12.3375, lon: float=75.8069,
    place: str="India", before_date: str | None=None, after_date: str | None=None,
):
    plan=parse_nl(q)
    live=await live_intelligence_ep(lat,lon,place,before_date,after_date,2.0,60)
    return {
        "query":plan,
        "live_result":live,
        "execution_note":"Natural-language intent was parsed, then executed against real provider-backed evidence for the selected location.",
    }


@app.get("/api/analysis/vegetation-series")
async def vegetation_series_ep(
    lat: float, lon: float, start: str, end: str, max_observations: int = Query(8, ge=3, le=16),
    cloud_lt: float = Query(50, ge=0, le=100), radius_km: float = Query(1.5, ge=.2, le=5),
):
    try:
        sdate=datetime.fromisoformat(start).replace(tzinfo=timezone.utc); edate=datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
    except Exception:
        raise HTTPException(422,"start/end must use YYYY-MM-DD")
    if edate <= sdate: raise HTTPException(422,"end must be after start")

    key=(
        f"vegetation-series:{round(lat,5)}:{round(lon,5)}:{start}:{end}:"
        f"{max_observations}:{round(cloud_lt,1)}:{round(radius_km,2)}"
    )

    async def produce():
        data=await earth.search(lat,lon,sdate,edate,cloud_lt=cloud_lt,limit=100)
        feats=sorted(data.get("features") or [],key=lambda f:(f.get("properties") or {}).get("datetime") or "")
        if not feats: raise HTTPException(404,"No suitable Sentinel-2 scenes found")
        if len(feats)>max_observations:
            import numpy as np
            idx=np.linspace(0,len(feats)-1,max_observations).round().astype(int)
            feats=[feats[int(i)] for i in sorted(set(idx.tolist()))]

        semaphore=asyncio.Semaphore(4)
        async def read_scene(feature):
            async with semaphore:
                try:
                    row=await asyncio.to_thread(scene_summary,feature,lat,lon,radius_km,.45)
                    return True,row
                except Exception as exc:
                    return False,{"scene":feature.get("id"),"error":str(exc)}

        results=await asyncio.gather(*(read_scene(f) for f in feats))
        rows=[value for ok,value in results if ok]
        errors=[value for ok,value in results if not ok]
        if len(rows)<2: raise HTTPException(503,"Too few Sentinel-2 scenes could be read for a time series")
        return {"source":"Sentinel-2 L2A / Earth Search","observations":rows,"errors":errors,"label":"DERIVED_METRIC"}

    return await cached_async(key,600,produce)


@app.get("/api/analysis/recovery-location")
async def recovery_location_ep(
    lat: float, lon: float, start: str, end: str, max_observations: int = Query(8, ge=3, le=16),
    cloud_lt: float = Query(50, ge=0, le=100), radius_km: float = Query(1.5, ge=.2, le=5),
):
    series=await vegetation_series_ep(lat,lon,start,end,max_observations,cloud_lt,radius_km)
    result=recovery_from_series(series["observations"])
    return {"recovery":result,"series":series,"warning":"Recovery is inferred from optical vegetation/forest-mask trends. Cloud/season effects and field conditions must be reviewed."}


@app.get("/api/analysis/climate-forest-correlation")
async def climate_forest_correlation_ep(
    lat: float, lon: float, start: str, end: str, max_observations: int = Query(8, ge=3, le=16),
    cloud_lt: float = Query(50, ge=0, le=100), radius_km: float = Query(1.5, ge=.2, le=5),
):
    import numpy as np
    series=await vegetation_series_ep(lat,lon,start,end,max_observations,cloud_lt,radius_km)
    hist,climate_source,provider_trace=await historical_climate_daily_real(lat,lon,start,end)
    daily=hist.get("daily") or {}; times=daily.get("time") or []; temps=daily.get("temperature_2m_mean") or []; rains=daily.get("precipitation_sum") or []
    lookup={d:(t,r) for d,t,r in zip(times,temps,rains) if t is not None and r is not None}
    rows=[]
    for obs in series["observations"]:
        day=(obs.get("datetime") or "")[:10]
        if day in lookup and obs.get("mean_ndvi") is not None and obs.get("forest_fraction") is not None:
            t,r=lookup[day]; rows.append({"date":day,"temperature_c":float(t),"rainfall_mm":float(r),"ndvi":float(obs["mean_ndvi"]),"forest_fraction":float(obs["forest_fraction"])})
    if len(rows)<3: raise HTTPException(422,"At least three date-matched climate/satellite observations are required")
    def corr(a,b):
        aa=np.array([x[a] for x in rows]); bb=np.array([x[b] for x in rows])
        return None if np.std(aa)==0 or np.std(bb)==0 else round(float(np.corrcoef(aa,bb)[0,1]),3)
    return {"observations":rows,"pearson":{"temperature__ndvi":corr("temperature_c","ndvi"),"rainfall__ndvi":corr("rainfall_mm","ndvi"),"temperature__forest_fraction":corr("temperature_c","forest_fraction"),"rainfall__forest_fraction":corr("rainfall_mm","forest_fraction")},"climate_source":climate_source,"provider_fallback_used":bool(provider_trace),"provider_trace":provider_trace,"label":"DERIVED_METRIC","warning":"Correlation is descriptive and does not establish causation."}


@app.post("/api/analysis/fragmentation")
async def fragmentation_ep(raster: UploadFile = File(...), threshold: float = Query(.5, ge=0, le=1)):
    try: return fragmentation_metrics(await raster.read(), threshold)
    except (FragmentationInputError, Exception) as e:
        raise HTTPException(422, str(e))


@app.post("/api/carbon")
def carbon_ep(req: CarbonRequest): return carbon_estimate(req)

@app.post("/api/patrol")
def patrol_ep(req: PatrolRequest):
    try: return patrol_optimize(req)
    except ValueError as e: raise HTTPException(422,str(e))

@app.post("/api/patrol/road-route")
async def patrol_road_route(req: PatrolRequest):
    raw_points=[(req.start_lat,req.start_lon)]+[(p.lat,p.lon) for p in req.points]
    table=None; table_error=None
    try: table=await osrm.table(raw_points)
    except Exception as exc: table_error=str(exc)
    try: ordering=patrol_optimize(req,(table or {}).get("durations"),(table or {}).get("distances"))
    except ValueError as e: raise HTTPException(422,str(e))
    ordered_points=[(req.start_lat,req.start_lon)]+[(x["lat"],x["lon"]) for x in ordering["route"]]
    try:
        road=await osrm.route(ordered_points)
        return {"ordering":ordering,"road_route":road,"route_summary":{"stops":ordering.get("stop_count"),"road_distance_km":road.get("distance_km"),"estimated_duration_min":road.get("duration_min"),"ordering_mode":ordering.get("ordering_mode"),"routing_source":road.get("source")},"matrix_error":table_error,"status":"ROAD_ROUTE_READY","warning":"OSM road/track completeness varies in forests. Verify patrol accessibility and field safety before deployment."}
    except Exception as exc:
        return {"ordering":ordering,"road_route":None,"route_summary":{"stops":ordering.get("stop_count"),"straight_line_km":ordering.get("estimated_straight_line_km"),"ordering_mode":ordering.get("ordering_mode")},"matrix_error":table_error,"routing_error":str(exc),"status":"ORDERING_ONLY","warning":"Road geometry is unavailable; priority-aware fallback ordering is shown. Do not treat straight lines as drivable roads."}

@app.get("/api/query")
def nl_query(q: str = Query(..., min_length=3)): return parse_nl(q)


@app.get("/api/report/investigation")
async def automatic_investigation_report(
    lat: float, lon: float, place: str = "India", before_date: str | None = None, after_date: str | None = None,
):
    data=await evidence_chain_ep(lat,lon,place,before_date,after_date,2.0,60)
    data["title"]="VanRakshak AI — Forest Investigation Report"
    return Response(investigation_pdf(data),media_type="application/pdf",headers={"Content-Disposition":"attachment; filename=vanrakshak-investigation-report.pdf"})


@app.post("/api/report")
def report(payload: dict):
    title = payload.get("title", "VanRakshak Investigation Report")
    lines = [f"Generated: {datetime.now(timezone.utc).isoformat()}"]
    for k, v in payload.items():
        if k != "title": lines.append(f"{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v}")
    return Response(pdf_report(title, lines), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=vanrakshak-report.pdf"})


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB = PROJECT_ROOT / "web"
if not WEB.exists(): WEB = Path("/web")
if WEB.exists(): app.mount("/static", StaticFiles(directory=str(WEB)), name="static")

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    p=WEB / "favicon.svg"
    return FileResponse(str(p),media_type="image/svg+xml") if p.exists() else Response(status_code=204)


@app.get("/")
def root():
    p = WEB / "index.html"
    return FileResponse(str(p)) if p.exists() else {"message": "VanRakshak AI API", "docs": "/docs"}

