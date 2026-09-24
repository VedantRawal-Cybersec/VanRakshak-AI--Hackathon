from __future__ import annotations
from typing import Any
from app.config import settings

async def geocode_search(nominatim, photon, q: str, limit: int = 5):
    errors=[]
    try:
        data=await nominatim.search(q,limit)
        if data:
            return {"source":"OpenStreetMap Nominatim","data":data,"degraded":False,"errors":errors}
    except Exception as exc:
        errors.append(f"Nominatim: {exc}")
    try:
        data=await photon.search(q,limit)
        return {"source":"Photon/OpenStreetMap fallback","data":data,"degraded":True,"errors":errors}
    except Exception as exc:
        errors.append(f"Photon: {exc}")
    raise RuntimeError("; ".join(errors) or "No geocoder available")

async def reverse_geocode(nominatim, photon, lat: float, lon: float):
    errors=[]
    try:
        data=await nominatim.reverse(lat,lon)
        if data:
            return {"source":"OpenStreetMap Nominatim","data":data,"degraded":False,"errors":errors}
    except Exception as exc:
        errors.append(f"Nominatim: {exc}")
    try:
        data=await photon.reverse(lat,lon)
        return {"source":"Photon/OpenStreetMap fallback","data":data,"degraded":True,"errors":errors}
    except Exception as exc:
        errors.append(f"Photon: {exc}")
    raise RuntimeError("; ".join(errors) or "No reverse geocoder available")

async def fire_rows(firms, eonet, lat: float, lon: float, days: int = 1):
    errors=[]
    if settings.firms_map_key:
        try:
            rows=await firms.fires(lat,lon,days=days)
            return {
                "source":"NASA FIRMS NOAA-21 + NOAA-20 + MODIS NRT",
                "freshness":"LIVE_NRT",
                "rows":rows,
                "degraded":False,
                "errors":errors,
                "note":"Multi-sensor FIRMS active-fire detections.",
            }
        except Exception as exc:
            errors.append(f"FIRMS: {exc}")
    else:
        errors.append("FIRMS: FIRMS_MAP_KEY not configured")
    try:
        rows=await eonet.wildfire_points(lat,lon,days=max(days,14),radius_deg=3)
        return {
            "source":"NASA EONET wildfire context fallback",
            "freshness":"DYNAMIC_RECENT",
            "rows":rows,
            "degraded":True,
            "errors":errors,
            "note":"Fallback natural-event context; these are not equivalent to FIRMS pixel-level thermal detections.",
        }
    except Exception as exc:
        errors.append(f"EONET: {exc}")
    raise RuntimeError("; ".join(errors))

async def protected_context(overpass, ee, lat: float, lon: float):
    errors=[]
    # Earth Engine WDPA is authoritative when authenticated.
    if settings.google_cloud_project:
        try:
            data=ee.sample("wdpa_protected",lat,lon,3650)
            return {
                "source":"UNEP-WCMC WDPA / Google Earth Engine",
                "inside":bool(data.get("inside_protected_area")),
                "areas":data.get("areas") or [],
                "raw":data,
                "degraded":False,
                "errors":errors,
            }
        except Exception as exc:
            errors.append(f"WDPA/Earth Engine: {exc}")
    try:
        data=await overpass.containing_protected_areas(lat,lon)
        areas=data.get("elements") or []
        return {
            "source":"OpenStreetMap protected-area fallback",
            "inside":bool(areas),
            "areas":[{"id":x.get("id"),"type":x.get("type"),"tags":x.get("tags") or {},"center":x.get("center")} for x in areas[:50]],
            "raw":{"count":len(areas)},
            "degraded":True,
            "errors":errors,
            "note":"OSM is a fallback reference and is not a substitute for authoritative Protected Planet/WDPA coverage.",
        }
    except Exception as exc:
        errors.append(f"OSM protected areas: {exc}")
    raise RuntimeError("; ".join(errors))

def provider_strategy():
    return {
        "satellite":{
            "primary":"Element 84 Earth Search / Sentinel-2",
            "fallbacks":["Copernicus Data Space STAC","NASA GIBS imagery"],
            "credential_free":True,
        },
        "fire":{
            "primary":"NASA FIRMS NOAA-21/NOAA-20/MODIS NRT",
            "fallbacks":["NASA EONET wildfire context","NASA GIBS imagery"],
            "credential_free_fallback":True,
        },
        "protected_areas":{
            "primary":"Protected Planet v4 / WDPA",
            "fallbacks":["Earth Engine WDPA when authenticated","OpenStreetMap protected-area fallback"],
            "credential_free_fallback":True,
        },
        "geocoding":{
            "primary":"Nominatim",
            "fallbacks":["Photon/OpenStreetMap"],
            "credential_free":True,
        },
        "forest_cover":{
            "primary":"Dynamic World when Earth Engine is authenticated",
            "fallbacks":["GFW tree-cover density","Sentinel-2 NDVI/forest mask"],
            "credential_free_fallback":True,
        },
        "historic_loss":{
            "primary":"GFW/Hansen public raster tiles",
            "fallbacks":["Earth Engine Hansen"],
            "credential_free":True,
        },
        "weather":{"primary":"Open-Meteo","fallbacks":[],"credential_free":True},
        "routing":{"primary":"OSRM/OpenStreetMap","fallbacks":["self-hosted OSRM via OSRM_URL"],"credential_free":True},
    }
