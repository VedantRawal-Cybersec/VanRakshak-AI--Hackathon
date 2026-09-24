from __future__ import annotations
import re

def parse(q: str):
    s=q.lower(); out={"raw":q,"filters":{}}
    states=["karnataka","kerala","maharashtra","odisha","madhya pradesh","chhattisgarh","assam","uttarakhand","tamil nadu"]
    for st in states:
        if st in s: out["filters"]["state"]=st.title()
    if "high heat" in s or "hot" in s: out["filters"]["temperature_anomaly_gte_c"]=1.5
    if "canopy loss" in s or "forest loss" in s: out["filters"]["forest_loss"] = True
    m=re.search(r"ndvi\s*(?:drop|loss)?\s*>?\s*(\d+)",s)
    if m: out["filters"]["ndvi_drop_gte_pct"]=int(m.group(1))
    if "fire" in s: out["filters"]["recent_fire"] = True
    if "protected" in s: out["filters"]["protected_area"] = True
    if "critical" in s: out["filters"]["severity"]="CRITICAL"
    out["explanation"]="Parsed into structured geospatial/environmental filters; the database/API layer should execute these filters."
    return out
