from __future__ import annotations
import asyncio, json, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))

from app.adapters import EarthSearchAdapter, OpenMeteoAdapter, GIBSAdapter

REGIONS=json.loads((ROOT/"config/demo_regions.json").read_text(encoding="utf-8"))

def dt(item):
    raw=(item.get("properties") or {}).get("datetime")
    return datetime.fromisoformat(raw.replace("Z","+00:00")) if raw else None

async def region_check(region):
    earth=EarthSearchAdapter(); weather=OpenMeteoAdapter(); gibs=GIBSAdapter()
    end=datetime.now(timezone.utc); start=end-timedelta(days=540)
    data=await earth.search(region["lat"],region["lon"],start,end,"sentinel-2-l2a",55,100)
    scenes=[x for x in data.get("features",[]) if dt(x)]
    scenes.sort(key=dt)
    # Pick a low-cloud pair separated by at least 45 days. This creates deterministic demo candidates
    # without hard-coding imagery that can disappear from a catalogue.
    pair=None
    best=None
    for i,b in enumerate(scenes):
        bp=b.get("properties") or {}
        for a in scenes[i+1:]:
            if (dt(a)-dt(b)).days < 45: continue
            ap=a.get("properties") or {}
            score=float(bp.get("eo:cloud_cover") or 100)+float(ap.get("eo:cloud_cover") or 100)
            if best is None or score<best:
                best=score; pair=(b,a)
    weather_ok=False
    try:
        weather_ok="current" in await weather.current(region["lat"],region["lon"])
    except Exception:
        pass
    gibs_ok=False
    try:
        gibs_ok=(await gibs.health()).get("ok") is True
    except Exception:
        pass
    out={"id":region["id"],"name":region["name"],"scene_count":len(scenes),"weather_ok":weather_ok,"gibs_ok":gibs_ok}
    if pair:
        out["before"]={"id":pair[0].get("id"),"date":dt(pair[0]).date().isoformat(),"cloud":(pair[0].get("properties") or {}).get("eo:cloud_cover")}
        out["after"]={"id":pair[1].get("id"),"date":dt(pair[1]).date().isoformat(),"cloud":(pair[1].get("properties") or {}).get("eo:cloud_cover")}
        out["ready"]=weather_ok and gibs_ok
    else:
        out["ready"]=False; out["error"]="No suitable Sentinel-2 pair >=45 days apart"
    return out

async def main():
    rows=[]
    for region in REGIONS:
        try: rows.append(await region_check(region))
        except Exception as exc: rows.append({"id":region["id"],"name":region["name"],"ready":False,"error":str(exc)})
    print(json.dumps({"generated_at":datetime.now(timezone.utc).isoformat(),"regions":rows},indent=2))
    ready=sum(1 for r in rows if r.get("ready"))
    print(f"Demo forests ready: {ready}/{len(rows)}")
    if ready<3:
        raise SystemExit("Need at least 3 demo-ready forests")
if __name__=="__main__":
    asyncio.run(main())
