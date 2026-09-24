import json
import urllib.request

BASE="https://earth-search.aws.element84.com/v1"
IDS=[
"S1A_IW_GRDH_1SDV_20251105T004827_20251105T004852_061735_07B71E",
"S1A_IW_GRDH_1SDV_20260209T004819_20260209T004844_063135_07ECBE",
]

def fetch(url):
    with urllib.request.urlopen(url,timeout=60) as r:
        return json.load(r)

for item_id in IDS:
    url=f"{BASE}/collections/sentinel-1-grd/items/{item_id}"
    item=fetch(url)
    p=item.get("properties") or {}
    vv=(item.get("assets") or {}).get("vv") or {}
    print("\nITEM",item_id)
    print("bbox",item.get("bbox"))
    print("geometry",json.dumps(item.get("geometry")))
    for k in ["datetime","sat:orbit_state","sat:relative_orbit","sat:relative_orbit_number","proj:epsg","proj:shape","proj:transform","proj:bbox"]:
        print(k,p.get(k))
    print("VV href",vv.get("href"))
    for k in ["proj:epsg","proj:shape","proj:transform","proj:bbox","raster:bands","roles","type"]:
        print("VV",k,vv.get(k))
