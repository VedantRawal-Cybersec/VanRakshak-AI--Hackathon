from __future__ import annotations
import asyncio, json, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))

from app.adapters import EarthSearchAdapter, OpenMeteoAdapter, EONETAdapter, OverpassAdapter, NominatimAdapter, GIBSAdapter

MANIFEST=ROOT/"config"/"demo_forests.json"

def scene_date(item):
    return ((item.get("properties") or {}).get("datetime") or "")[:10]

def choose_pair(features):
    good=sorted(features,key=lambda f:(((f.get("properties") or {}).get("eo:cloud_cover") or 1000), scene_date(f)))
    if len(good)<2:
        return None
    # Prefer a pair separated by at least ~90 days, then lowest combined cloud.
    best=None
    for i,a in enumerate(good):
        da=scene_date(a)
        if not da: continue
        dta=datetime.fromisoformat(da)
        for b in good[i+1:]:
            db=scene_date(b)
            if not db: continue
            dtb=datetime.fromisoformat(db)
            gap=abs((dtb-dta).days)
            if gap<90: continue
            ca=float((a.get("properties") or {}).get("eo:cloud_cover") or 100)
            cb=float((b.get("properties") or {}).get("eo:cloud_cover") or 100)
            score=ca+cb-(min(gap,365)/365)*5
            if best is None or score<best[0]:
                first,second=sorted([a,b],key=scene_date)
                best=(score,first,second)
    if best:
        return best[1],best[2]
    return good[0],good[1]

async def one(region):
    lat,lon=region["lat"],region["lon"]
    earth=EarthSearchAdapter(); meteo=OpenMeteoAdapter(); eonet=EONETAdapter(); over=OverpassAdapter(); nom=NominatimAdapter(); gibs=GIBSAdapter()
    end=datetime.now(timezone.utc); start=end-timedelta(days=730)
    result={"id":region["id"],"name":region["name"],"lat":lat,"lon":lon,"ok":True,"checks":{}}
    try:
        stac=await earth.search(lat,lon,start,end,"sentinel-2-l2a",70,60)
        features=stac.get("features") or []
        pair=choose_pair(features)
        result["checks"]["sentinel2"]={"ok":bool(pair),"scene_count":len(features)}
        if pair:
            bdate=datetime.fromisoformat(scene_date(pair[0])).replace(tzinfo=timezone.utc)
            adate=datetime.fromisoformat(scene_date(pair[1])).replace(tzinfo=timezone.utc)
            sar_pair=await earth.closest_sentinel1_pair(lat,lon,bdate,adate,30)
            result["recommended_demo"]={
                "before":{"id":pair[0].get("id"),"date":scene_date(pair[0]),"cloud":(pair[0].get("properties") or {}).get("eo:cloud_cover")},
                "after":{"id":pair[1].get("id"),"date":scene_date(pair[1]),"cloud":(pair[1].get("properties") or {}).get("eo:cloud_cover")},
                "sar_matched_pair": bool(sar_pair),
                "sar_before": (sar_pair[0].get("id") if sar_pair else None),
                "sar_after": (sar_pair[1].get("id") if sar_pair else None),
            }
            result["checks"]["sentinel1_matched_pair"]={"ok":bool(sar_pair)}
        else:
            result["ok"]=False
    except Exception as exc:
        result["checks"]["sentinel2"]={"ok":False,"error":str(exc)}
        result["ok"]=False
    async def probe(label,coro,validator=lambda x:bool(x)):
        try:
            value=await coro
            result["checks"][label]={"ok":bool(validator(value))}
        except Exception as exc:
            result["checks"][label]={"ok":False,"error":str(exc)}
    await asyncio.gather(
        probe("weather",meteo.current(lat,lon),lambda x:isinstance(x,dict) and "current" in x),
        probe("eonet",eonet.events(lat,lon,30,3,10),lambda x:isinstance(x,dict) and "events" in x),
        probe("protected_fallback",over.containing_protected_areas(lat,lon),lambda x:isinstance(x,dict) and "elements" in x),
        probe("reverse_geocode",nom.reverse(lat,lon),lambda x:isinstance(x,dict) and bool(x)),
        probe("gibs",gibs.health(),lambda x:isinstance(x,dict) and x.get("ok") is True),
    )
    if not result["checks"].get("weather",{}).get("ok"):
        result["ok"]=False
    return result

async def main():
    regions=json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows=[]
    for r in regions:
        rows.append(await one(r))
    payload={"generated_at":datetime.now(timezone.utc).isoformat(),"regions":rows}
    print(json.dumps(payload,indent=2))
    failed=[r["name"] for r in rows if not r["ok"]]
    if failed:
        print("Demo preflight failed for: "+", ".join(failed),file=sys.stderr)
        return 1
    return 0

if __name__=="__main__":
    raise SystemExit(asyncio.run(main()))
