from __future__ import annotations
from datetime import datetime, timezone


def _num(value, default=None):
    try:
        return float(value)
    except Exception:
        return default


def _centroid(feature: dict):
    geom=(feature or {}).get("geometry") or {}
    coords=geom.get("coordinates")
    pts=[]
    def walk(x):
        if isinstance(x,(list,tuple)) and len(x)>=2 and all(isinstance(v,(int,float)) for v in x[:2]):
            pts.append((float(x[1]),float(x[0])))
        elif isinstance(x,(list,tuple)):
            for y in x:
                walk(y)
    walk(coords)
    if not pts:
        return None
    return (sum(x[0] for x in pts)/len(pts),sum(x[1] for x in pts)/len(pts))


def compose_patrol_alert(bundle: dict, lat: float, lon: float, place: str, incident_id: str):
    change=bundle.get("change") or {}
    warning=bundle.get("warning") or {}
    doctor=bundle.get("forest_doctor") or {}
    sources=bundle.get("sources") or {}
    features=((change.get("geojson") or {}).get("features") or [])

    ranked=sorted(
        features,
        key=lambda f:_num(((f.get("properties") or {}).get("area_ha")),0.0) or 0.0,
        reverse=True,
    )
    top=ranked[0] if ranked else None
    top_center=_centroid(top) if top else None
    top_area=_num(((top or {}).get("properties") or {}).get("area_ha"))

    area=_num(change.get("candidate_area_ha"))
    ndvi=_num(change.get("mean_ndvi_change"))
    confidence=_num(change.get("screening_confidence"))
    score=_num(warning.get("score"))
    severity=str(warning.get("level") or "UNKNOWN").upper()

    before=change.get("before") or {}
    after=change.get("after") or {}
    before_at=str(before.get("datetime") or "")[:10] or "unknown"
    after_at=str(after.get("datetime") or "")[:10] or "unknown"

    drivers=doctor.get("probable_drivers") or []
    driver_rows=[]
    for row in drivers[:3]:
        if not isinstance(row,dict):
            continue
        name=str(row.get("driver") or "").strip()
        support=_num(row.get("relative_support_pct"))
        if name:
            driver_rows.append({
                "driver":name,
                "support_pct":round(support,1) if support is not None else None,
            })

    fire=sources.get("fire") or {}
    fire_count=len(fire.get("data") or []) if fire.get("ok") else None
    fire_source=((fire.get("provenance") or {}).get("source") or "fire source")
    protected=bundle.get("protected_area")
    protected_text="inside/overlapping a protected-area context" if protected is True else "outside the returned protected-area context" if protected is False else "protected-area status not confirmed"

    map_url=f"https://www.google.com/maps?q={lat:.6f},{lon:.6f}"
    hotspot_url=f"https://www.google.com/maps?q={top_center[0]:.6f},{top_center[1]:.6f}" if top_center else map_url

    if driver_rows:
        how_text=", ".join(
            f"{x['driver']} ({x['support_pct']:.0f}% relative support)" if x["support_pct"] is not None else x["driver"]
            for x in driver_rows
        )
    else:
        how_text="Cause is not established from the current evidence; field verification is required."

    what_parts=[]
    if area is not None:
        what_parts.append(f"{area:.2f} ha candidate vegetation/forest change")
    if features:
        what_parts.append(f"{len(features)} detected change polygon{'s' if len(features)!=1 else ''}")
    if ndvi is not None:
        what_parts.append(f"mean NDVI change {ndvi:+.3f}")
    what_text=", ".join(what_parts) if what_parts else "No complete candidate-change measurement is available."

    confidence_text=f"{confidence*100:.0f}%" if confidence is not None else "not available"
    score_text=f"{score:.0f}/100" if score is not None else "not available"
    top_text=(
        f"{top_center[0]:.6f}, {top_center[1]:.6f}"
        + (f" ({top_area:.2f} ha candidate polygon)" if top_area is not None else "")
        if top_center else f"{lat:.6f}, {lon:.6f}"
    )

    recommended_actions=[
        f"Dispatch a patrol team to the priority coordinates: {top_text}.",
        "Verify the change on the ground and capture geotagged photos/video plus access-road observations.",
        "Record signs of cutting, fire, clearing, vehicle access, encroachment or other disturbance without assuming a cause in advance.",
        "Escalate to the responsible forest authority only if field evidence confirms an actionable incident.",
    ]

    message_lines=[
        "🚨 VANRAKSHAK AI — PATROL ALERT",
        f"Incident: {incident_id}",
        f"Severity: {severity} | Warning score: {score_text}",
        "",
        f"WHERE: {place} | {lat:.6f}, {lon:.6f}",
        f"Map: {map_url}",
        "",
        f"WHAT WAS DETECTED: {what_text}.",
        f"WHEN: satellite comparison {before_at} → {after_at}.",
        f"EVIDENCE CONFIDENCE: {confidence_text} screening confidence; status is {protected_text}.",
        "",
        f"HOW IT MAY BE HAPPENING: {how_text}",
    ]
    if fire_count is not None:
        message_lines.append(f"FIRE CONTEXT: {fire_count} contextual detection/event row(s) from {fire_source}.")
    message_lines += [
        "",
        f"PATROL FIRST PRIORITY: {top_text}",
        f"Priority map: {hotspot_url}",
        "",
        "RECOMMENDED FIELD ACTION:",
    ]
    message_lines += [f"{i+1}. {x}" for i,x in enumerate(recommended_actions)]
    message_lines += [
        "",
        "IMPORTANT: Satellite screening identifies candidate change, not proof of illegal deforestation or a confirmed cause. Verify with field evidence.",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
    ]

    return {
        "incident_id":incident_id,
        "subject":f"[{severity}] VanRakshak patrol alert — {place} — {incident_id}",
        "severity":severity,
        "warning_score":round(score,1) if score is not None else None,
        "location":{"place":place,"lat":lat,"lon":lon,"map_url":map_url},
        "detected_period":{"before":before_at,"after":after_at},
        "change":{"candidate_area_ha":round(area,3) if area is not None else None,"candidate_polygons":len(features),"mean_ndvi_change":round(ndvi,4) if ndvi is not None else None,"screening_confidence":round(confidence,3) if confidence is not None else None},
        "probable_drivers":driver_rows,
        "top_patrol_target":{"lat":top_center[0],"lon":top_center[1],"area_ha":top_area,"map_url":hotspot_url} if top_center else {"lat":lat,"lon":lon,"area_ha":None,"map_url":map_url},
        "recommended_actions":recommended_actions,
        "message":"\n".join(message_lines),
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "label":"DERIVED_FROM_REAL_EVIDENCE",
        "warning":"This alert is a screening brief for patrol triage. It does not establish illegality or causation without field verification.",
    }
