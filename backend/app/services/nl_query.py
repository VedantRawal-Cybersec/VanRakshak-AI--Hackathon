from __future__ import annotations
import re
from datetime import date, timedelta

INDIA_STATES_UTS = [
"andhra pradesh","arunachal pradesh","assam","bihar","chhattisgarh","goa","gujarat","haryana","himachal pradesh","jharkhand","karnataka","kerala","madhya pradesh","maharashtra","manipur","meghalaya","mizoram","nagaland","odisha","punjab","rajasthan","sikkim","tamil nadu","telangana","tripura","uttar pradesh","uttarakhand","west bengal","andaman and nicobar islands","chandigarh","dadra and nagar haveli and daman and diu","delhi","jammu and kashmir","ladakh","lakshadweep","puducherry"
]


def parse(q: str):
    s=" "+q.lower().strip()+" "; filters={}; layers=[]; actions=[]
    for st in INDIA_STATES_UTS:
        if f" {st} " in s:
            filters["state"]=st.title(); break
    if re.search(r"\b(high heat|very hot|heat stress|hotspot heat)\b",s): filters["temperature_anomaly_gte_c"]=1.5
    if re.search(r"\b(canopy loss|forest loss|deforestation|tree loss|clearing)\b",s):
        filters["forest_loss"]=True; layers.append("forest_loss"); actions.append("investigate_change")
    m=re.search(r"ndvi\s*(?:drop|loss)?\s*(?:>=?|at least)?\s*(\d+(?:\.\d+)?)\s*%?",s)
    if m: filters["ndvi_drop_gte_pct"]=float(m.group(1)); layers.append("ndvi")
    if re.search(r"\b(fire|burn|wildfire|thermal)\b",s): filters["recent_fire"]=True; layers.append("active_fire")
    if re.search(r"\b(protected|national park|sanctuary|reserve)\b",s): filters["protected_area"]=True; layers.append("protected")
    if re.search(r"\b(drought|water stress|dryness)\b",s): filters["drought"]=True; layers += ["soil_moisture","drought"]
    if re.search(r"\b(carbon|biomass|co2)\b",s): filters["carbon"]=True; layers += ["carbon_stock","biomass"]
    if re.search(r"\b(road|settlement|village|mining|quarry|human pressure)\b",s): filters["human_pressure"]=True; layers += ["roads","settlements","industrial"]
    sev=re.search(r"\b(normal|watch|warning|critical)\b",s)
    if sev: filters["severity"]=sev.group(1).upper()
    conf=re.search(r"\b(high|nominal|low) confidence\b",s)
    if conf: filters["confidence"]=conf.group(1)
    cloud=re.search(r"cloud(?: cover)?\s*(?:under|below|<|<=)\s*(\d+(?:\.\d+)?)\s*%",s)
    if cloud: filters["cloud_cover_lte_pct"]=float(cloud.group(1))

    today=date.today()
    if "last 7 days" in s or "past week" in s: filters["date_range"]=[(today-timedelta(days=7)).isoformat(),today.isoformat()]
    elif "last 30 days" in s or "past month" in s: filters["date_range"]=[(today-timedelta(days=30)).isoformat(),today.isoformat()]
    elif "last year" in s or "past year" in s: filters["date_range"]=[(today-timedelta(days=365)).isoformat(),today.isoformat()]
    years=re.findall(r"\b(20\d{2})\b",s)
    if len(years)>=2:
        a,b=sorted(years[:2]); filters["date_range"]=[f"{a}-01-01",f"{b}-12-31"]
    elif len(years)==1 and "date_range" not in filters:
        filters["year"]=int(years[0])

    if "compare" in s or "before" in s and "after" in s: actions.append("before_after")
    if "predict" in s or "future risk" in s or "threat" in s: actions.append("predict")
    if "patrol" in s or "route" in s: actions.append("patrol")
    if "report" in s: actions.append("report")
    if "news" in s or "why" in s or "cause" in s: actions.append("evidence_chain")

    layers=list(dict.fromkeys(layers))
    plan=[]
    if filters.get("forest_loss") or "investigate_change" in actions: plan.append({"endpoint":"/api/analysis/evidence-chain","purpose":"multi-source forest disturbance investigation"})
    if filters.get("recent_fire"): plan.append({"endpoint":"/api/fire","purpose":"NRT fire verification"})
    if filters.get("drought") or "temperature_anomaly_gte_c" in filters: plan.append({"endpoint":"/api/climate/anomaly","purpose":"historical climate anomaly"})
    if filters.get("human_pressure"): plan.append({"endpoint":"/api/human-pressure","purpose":"mapped roads/settlements/industrial pressure"})
    if "predict" in actions: plan.append({"endpoint":"/api/intelligence/predict","purpose":"transparent trend projection"})
    if "patrol" in actions: plan.append({"endpoint":"/api/patrol/road-route","purpose":"road-aware patrol routing"})
    if "report" in actions: plan.append({"endpoint":"/api/report/investigation","purpose":"automatic evidence report"})
    return {
        "raw":q,"filters":filters,"layers":layers,"actions":list(dict.fromkeys(actions)),"query_plan":plan,
        "explanation":"Natural language is converted to a validated structured plan; actual geospatial/API services execute the query so the language layer cannot invent map results.",
    }
