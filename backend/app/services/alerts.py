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
    climate=bundle.get("climate") or {}
    carbon=bundle.get("carbon") or {}
    action_plan=bundle.get("action_plan") or {}
    frag=((change.get("fragmentation") or {}).get("change") or change.get("fragmentation_change") or {})
    hp=sources.get("human_pressure") or {}
    hp_data=hp.get("data") or {}
    human_pressure_count=None
    if isinstance(hp_data,dict):
        human_pressure_count=hp_data.get("count")
        if human_pressure_count is None and isinstance(hp_data.get("elements"),list):
            human_pressure_count=len(hp_data.get("elements") or [])

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

    plan_actions=action_plan.get("actions") or []
    if plan_actions:
        recommended_actions=[
            f"{x.get('what')}: {x.get('how')}"
            for x in plan_actions[:4] if isinstance(x,dict) and x.get("what") and x.get("how")
        ]
    else:
        recommended_actions=[
            f"Dispatch a patrol team to the priority coordinates: {top_text}.",
            "Verify the change on the ground and capture geotagged photos/video plus access-road observations.",
            "Record signs of cutting, fire, clearing, vehicle access, encroachment or other disturbance without assuming a cause in advance.",
            "Escalate to the responsible forest authority only if field evidence confirms an actionable incident.",
        ]

    generated_at=datetime.now(timezone.utc).isoformat()
    alerts=[]

    def matched_plan(*terms):
        for row in plan_actions:
            if not isinstance(row,dict):
                continue
            hay=" ".join(str(row.get(k) or "") for k in ("what","why","how")).lower()
            if any(t.lower() in hay for t in terms):
                return row
        return None

    def add_alert(alert_id,kind,title,level,when,summary,evidence,plan=None,expected=None):
        alerts.append({
            "id":alert_id,
            "kind":kind,
            "title":title,
            "severity":level,
            "when":when,
            "summary":summary,
            "evidence":evidence,
            "plan":plan or "Review the evidence and field-verify before escalation.",
            "expected_impact":expected or "Create a verified before/after record and prevent unexplained worsening on the next observation.",
        })

    change_plan=matched_plan("ground-verify","vegetation change","disturbance")
    if area is not None and area>0:
        add_alert(
            "forest-change","FOREST_CHANGE","Candidate forest / vegetation change",
            severity,after_at,
            f"{area:.2f} ha candidate change across {len(features)} polygon(s); mean NDVI change {ndvi:+.3f}." if ndvi is not None else f"{area:.2f} ha candidate change across {len(features)} polygon(s).",
            f"Sentinel-2 before/after screening; confidence {confidence_text}.",
            change_plan.get("how") if change_plan else None,
            change_plan.get("expected_impact") if change_plan else None,
        )

    vegetation_plan=matched_plan("vegetation","ndvi","climate stress")
    if ndvi is not None and ndvi <= -0.03:
        veg_level="HIGH" if ndvi <= -0.10 else "WATCH"
        add_alert(
            "vegetation-stress","VEGETATION","Vegetation condition declining",
            veg_level,after_at,
            f"Mean NDVI changed by {ndvi:+.3f} across the comparison window.",
            "Cloud-masked multispectral vegetation index screening.",
            vegetation_plan.get("how") if vegetation_plan else "Compare NDVI with rainfall, soil moisture, fire context and field observations before assigning a cause.",
            vegetation_plan.get("expected_impact") if vegetation_plan else "NDVI should be stable or improving on the next suitable cloud-screened observation if stress/disturbance has stopped.",
        )

    fire_plan=matched_plan("fire","thermal","heat")
    if fire_count is not None and fire_count>0:
        add_alert(
            "fire-context","FIRE","Fire / heat context detected",
            "URGENT" if "FIRMS" in fire_source else "WATCH",
            str(((fire.get("provenance") or {}).get("observed_at") or generated_at))[:19],
            f"{fire_count} fire-context row(s) returned near the selected area.",
            f"Source: {fire_source}. EONET rows are contextual events; FIRMS rows are thermal detections.",
            fire_plan.get("how") if fire_plan else "Verify thermal points, weather and patrol access before dispatch.",
            fire_plan.get("expected_impact") if fire_plan else "No new verified thermal detections in the AOI after response.",
        )

    rain_def=_num(climate.get("rainfall_deficit_pct"))
    temp_anom=_num(climate.get("temperature_anomaly_c"))
    climate_plan=matched_plan("climate stress","rainfall","temperature")
    if (rain_def is not None and rain_def>=25) or (temp_anom is not None and temp_anom>=1.5):
        add_alert(
            "climate-stress","CLIMATE","Climate stress affecting forest interpretation",
            "WATCH",str((climate.get("window") or {}).get("end") or generated_at)[:19],
            f"Temperature anomaly {temp_anom:+.2f}°C; rainfall deficit {rain_def:.1f}%." if temp_anom is not None and rain_def is not None else "Climate anomaly threshold exceeded.",
            f"Historical/reanalysis comparison over {(climate.get('window') or {}).get('days') or 'recent'} days.",
            climate_plan.get("how") if climate_plan else "Recheck vegetation indices together with rainfall and soil moisture before classifying browning as clearing.",
            climate_plan.get("expected_impact") if climate_plan else "Reduce false escalation by separating climate-driven stress from direct forest removal.",
        )

    frag_value=next((frag.get(k) for k in ("patch_count_pct","patch_density_pct","edge_density_pct") if frag.get(k) is not None),None)
    frag_plan=matched_plan("fragmentation","corridor","forest-edge")
    if frag_value is not None and abs(float(frag_value))>=5:
        add_alert(
            "fragmentation","FRAGMENTATION","Forest fragmentation changed",
            "HIGH" if float(frag_value)>15 else "WATCH",after_at,
            f"Fragmentation metric changed by {float(frag_value):+.1f}% in the screened AOI.",
            "Derived from the same NDVI-threshold forest masks used for before/after screening.",
            frag_plan.get("how") if frag_plan else "Prioritize new edges, narrow connectors and patch breaks for field verification.",
            frag_plan.get("expected_impact") if frag_plan else "No worsening of patch/edge fragmentation around the same geometry on follow-up imagery.",
        )

    protected_plan=matched_plan("protected-area","protected area")
    if protected is True:
        add_alert(
            "protected-area","PROTECTED_AREA","Candidate change intersects protected-area context",
            "URGENT","Reference context",
            "The selected location is inside/overlapping the returned protected-area context.",
            str(((sources.get("protected_area") or {}).get("provenance") or {}).get("source") or "Protected-area intelligence"),
            protected_plan.get("how") if protected_plan else "Escalate the evidence package through the responsible protected-area workflow after field verification.",
            protected_plan.get("expected_impact") if protected_plan else "Faster evidence handoff with a preserved source and location trail.",
        )

    access_plan=matched_plan("access-route","settlement","human-pressure")
    if human_pressure_count is not None and human_pressure_count>0:
        add_alert(
            "human-pressure","HUMAN_PRESSURE","Mapped human-pressure context near AOI",
            "WATCH","Current map context",
            f"{human_pressure_count} mapped access/settlement/quarry-related context feature(s) returned.",
            str((hp.get("provenance") or {}).get("source") or "OpenStreetMap / Overpass"),
            access_plan.get("how") if access_plan else "Prioritize access routes and settlement edges for patrol verification without assuming causation.",
            access_plan.get("expected_impact") if access_plan else "Concentrate patrol time on plausible access points and document whether disturbance is actually present.",
        )

    co2=_num(carbon.get("estimated_co2e_t"))
    if co2 is not None and co2>0:
        add_alert(
            "carbon-impact","CARBON","Estimated carbon impact",
            "INFO",after_at,
            f"Estimated {co2:.1f} tCO₂e associated with the candidate affected area.",
            str(carbon.get("density_source") or carbon.get("estimate_class") or "Carbon reference model"),
            "Use the estimate for prioritization/reporting; replace with local biomass/field inventory when available.",
            "Prevent further candidate-area expansion and retain the estimate as a before/after ecological-impact baseline.",
        )

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
        f"Generated: {generated_at}",
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
        "alerts":alerts,
        "action_plan":action_plan,
        "impact_summary":{
            "carbon":carbon,
            "protected_area":protected,
            "vegetation":{"mean_ndvi_change":ndvi,"condition":"declining" if ndvi is not None and ndvi < -0.03 else "stable_or_improving" if ndvi is not None else "unknown"},
            "fragmentation":frag,
        },
        "message":"\n".join(message_lines),
        "generated_at":generated_at,
        "label":"DERIVED_FROM_REAL_EVIDENCE",
        "warning":"This alert is a screening brief for patrol triage. It does not establish illegality or causation without field verification.",
    }
