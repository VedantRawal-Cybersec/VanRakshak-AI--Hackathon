from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from math import radians, sin, cos, asin, sqrt



def _haversine(lat1,lon1,lat2,lon2):
    p1,p2=radians(lat1),radians(lat2); dlat=radians(lat2-lat1); dlon=radians(lon2-lon1)
    a=sin(dlat/2)**2+cos(p1)*cos(p2)*sin(dlon/2)**2
    return 6371*2*asin(sqrt(a))

def pressure_context(result: dict, lat: float, lon: float) -> dict:
    data=(result or {}).get("data") or {}
    els=data.get("elements") or [] if isinstance(data,dict) else []
    nearest_road=None; nearest_settlement=None; mining=False; categories={"roads":0,"settlements":0,"industrial_quarry_mine":0}
    for e in els:
        tags=e.get("tags") or {}
        c=e.get("center") or {}
        elat=e.get("lat",c.get("lat")); elon=e.get("lon",c.get("lon"))
        dist=_haversine(lat,lon,float(elat),float(elon)) if elat is not None and elon is not None else None
        if "highway" in tags:
            categories["roads"]+=1
            if dist is not None: nearest_road=dist if nearest_road is None else min(nearest_road,dist)
        if tags.get("place") in {"village","town","city","hamlet"}:
            categories["settlements"]+=1
            if dist is not None: nearest_settlement=dist if nearest_settlement is None else min(nearest_settlement,dist)
        if tags.get("landuse") in {"industrial","quarry","construction"} or tags.get("man_made")=="mineshaft":
            categories["industrial_quarry_mine"]+=1
            mining=True
    return {"nearest_road_km":round(nearest_road,3) if nearest_road is not None else None,"nearest_settlement_km":round(nearest_settlement,3) if nearest_settlement is not None else None,"mining_or_quarry_nearby":mining,"counts":categories}

def evidence_item(kind: str, source: str, statement: str, value: Any = None, observed_at: str | None = None,
                  confidence: float | None = None, url: str | None = None) -> dict:
    return {
        "kind": kind,
        "source": source,
        "statement": statement,
        "value": value,
        "observed_at": observed_at,
        "confidence": confidence,
        "source_url": url,
    }


def build_chain(sources: dict, change: dict | None = None, climate: dict | None = None) -> dict:
    items: list[dict] = []
    missing: list[str] = []

    if change:
        items.append(evidence_item(
            "DERIVED_METRIC", "Sentinel-2 / Earth Search",
            "Before/after cloud-masked spectral screening found candidate vegetation-loss pixels.",
            {"candidate_area_ha": change.get("candidate_area_ha"), "mean_ndvi_change": change.get("mean_ndvi_change")},
            change.get("after", {}).get("datetime"), change.get("screening_confidence"),
            "https://earth-search.aws.element84.com/v1",
        ))
    else:
        missing.append("before_after_change")

    fire = sources.get("fire") or {}
    if fire.get("ok"):
        rows = fire.get("data") or []
        p = fire.get("provenance") or {}
        src = p.get("source") or "NASA fire intelligence"
        if "EONET" in src:
            statement = f"{len(rows)} EONET wildfire-context events returned near the selected area; these are not pixel-level FIRMS thermal detections."
            kind = "EVENT_CONTEXT"
        else:
            statement = f"{len(rows)} multi-sensor NASA FIRMS thermal detections returned in the configured window."
            kind = "DIRECT_OBSERVATION"
        items.append(evidence_item(
            kind, src, statement, {"count": len(rows)}, p.get("observed_at"), url=source_url(fire),
        ))
    else:
        missing.append("fire")

    natural = sources.get("natural_events") or {}
    if natural.get("ok"):
        events=(natural.get("data") or {}).get("events") or []
        if events:
            items.append(evidence_item(
                "EVENT_CONTEXT", "NASA EONET",
                "Recent NASA-tracked natural events overlap the broader investigation window and are retained as context only.",
                {"event_count":len(events),"events":[{"id":e.get("id"),"title":e.get("title")} for e in events[:5]]},
                url=source_url(natural),
            ))

    protected = sources.get("protected_area") or {}
    if protected.get("ok"):
        pdata=protected.get("data") or {}
        inside=pdata.get("inside")
        items.append(evidence_item(
            "REFERENCE_DATA", pdata.get("source") or "Protected-area intelligence",
            "Protected-area containment/context was checked for the selected location.",
            {"inside_protected_area":inside,"areas":(pdata.get("areas") or [])[:5]},
            url=source_url(protected),
        ))
    else:
        missing.append("protected_area")

    hp = sources.get("human_pressure") or {}
    if hp.get("ok"):
        data = hp.get("data") or {}
        count = data.get("count", len(data.get("elements") or [])) if isinstance(data, dict) else None
        items.append(evidence_item(
            "REFERENCE_DATA", "OpenStreetMap / Overpass",
            "Mapped human-pressure features were found near the selected location; map completeness varies.",
            {"mapped_features": count}, url=source_url(hp),
        ))
    else:
        missing.append("human_pressure")

    weather = sources.get("weather") or {}
    if weather.get("ok"):
        cur = (weather.get("data") or {}).get("current") or {}
        items.append(evidence_item(
            "FORECAST", "Open-Meteo", "Current/forecast environmental context for the selected location.",
            {k: cur.get(k) for k in ("temperature_2m", "relative_humidity_2m", "rain", "cloud_cover", "wind_speed_10m")},
            cur.get("time"), url=source_url(weather),
        ))
    else:
        missing.append("weather")

    if climate:
        items.append(evidence_item(
            "DERIVED_METRIC", "Open-Meteo historical/reanalysis",
            "Temperature and rainfall conditions were compared with same-season historical baselines.",
            climate, url="https://open-meteo.com/en/docs/historical-weather-api",
        ))
    else:
        missing.append("climate_anomaly")

    s1 = sources.get("sentinel1") or {}
    if s1.get("ok"):
        data=s1.get("data") or {}
        count=len(data.get("features") or []) if isinstance(data,dict) else None
        items.append(evidence_item(
            "DIRECT_OBSERVATION", "ASF DAAC Sentinel-1", "Radar scenes are available for independent follow-up/confirmation.",
            {"scene_count": count}, url=source_url(s1),
        ))
    else:
        missing.append("sentinel1")

    news = sources.get("news") or {}
    if news.get("ok"):
        arts=(news.get("data") or {}).get("articles") or []
        items.append(evidence_item(
            "NEWS_CONTEXT", "GDELT", "Recent matching news was retrieved as contextual evidence only, never proof of cause.",
            {"article_count": len(arts), "articles": [
                {"title":a.get("title"),"url":a.get("url"),"domain":a.get("domain"),"seendate":a.get("seendate")} for a in arts[:5]
            ]}, url=source_url(news),
        ))
    else:
        missing.append("news")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
        "missing_evidence": missing,
        "interpretation_rule": "Evidence supports investigation prioritization; it does not establish illegality or legal causation.",
    }


def source_url(result: dict) -> str | None:
    return (result.get("provenance") or {}).get("source_url") if isinstance(result,dict) else None


def partial_risk(change: dict | None, sources: dict, climate: dict | None = None, protected_area: bool | None = None) -> dict:
    """Evidence-normalized 0..100 warning score that does not treat missing evidence as zero risk."""
    factors=[]
    def add(name: str, normalized: float | None, weight: float, evidence: str):
        if normalized is None: return
        normalized=max(0.0,min(1.0,float(normalized)))
        factors.append({"factor":name,"normalized":round(normalized,3),"weight":weight,"raw_contribution":normalized*weight,"evidence":evidence})

    if change:
        ndvi=change.get("mean_ndvi_change")
        area=change.get("candidate_area_ha")
        conf=change.get("screening_confidence")
        add("Spectral vegetation loss", min(1, max(0, -(ndvi or 0))/0.45) if ndvi is not None else None, 30, "Sentinel-2 NDVI change")
        add("Candidate affected area", min(1, (area or 0)/25) if area is not None else None, 12, "Sentinel-2 candidate loss polygon")
        add("Screening confidence", conf, 8, "Screening quality heuristic; not model accuracy")

    fire=sources.get("fire") or {}
    if fire.get("ok"):
        add("Fire activity", min(1,len(fire.get("data") or [])/10), 14, "NASA FIRMS")
    hp=sources.get("human_pressure") or {}
    if hp.get("ok"):
        d=hp.get("data") or {}; count=d.get("count",len(d.get("elements") or [])) if isinstance(d,dict) else 0
        add("Mapped human pressure", min(1,(count or 0)/80), 10, "OpenStreetMap; absence is not proof of no pressure")
    if climate:
        ta=climate.get("temperature_anomaly_c")
        rd=climate.get("rainfall_deficit_pct")
        add("Temperature anomaly", min(1,max(0,ta or 0)/4) if ta is not None else None, 10, "Historical climate baseline")
        add("Rainfall deficit", min(1,max(0,rd or 0)/70) if rd is not None else None, 10, "Historical climate baseline")
    if protected_area is not None:
        add("Protected-area sensitivity", 1 if protected_area else 0, 10, "UNEP-WCMC WDPA / Protected Planet")

    available_weight=sum(f["weight"] for f in factors)
    if not factors or available_weight<=0:
        return {"score":None,"level":"UNKNOWN","factors":[],"coverage":0,"label":"AI_ESTIMATE","warning":"Insufficient evidence to score."}
    weighted=sum(f["raw_contribution"] for f in factors)
    score=round(weighted/available_weight*100,1)
    for f in factors: f["contribution"]=round(f.pop("raw_contribution")/available_weight*100,1)
    level="NORMAL" if score<25 else "WATCH" if score<50 else "WARNING" if score<75 else "CRITICAL"
    return {"score":score,"level":level,"factors":sorted(factors,key=lambda x:x["contribution"],reverse=True),"coverage":round(available_weight/104,2),"label":"AI_ESTIMATE","method":"evidence-normalized transparent warning score; missing sources are excluded, not zero-filled"}
