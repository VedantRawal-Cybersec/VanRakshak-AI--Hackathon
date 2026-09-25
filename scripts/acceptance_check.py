from __future__ import annotations
from pathlib import Path
import re, sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))

from app.main import app
from app.services.feature_status import FEATURE_CAPABILITIES
from app.services.layers import LAYER_GROUPS

errors=[]

# 1) Exactly 37 discussed product capabilities.
if len(FEATURE_CAPABILITIES)!=37:
    errors.append(f"Expected 37 features, found {len(FEATURE_CAPABILITIES)}")
ids=[x.get("id") for x in FEATURE_CAPABILITIES]
if ids!=list(range(1,38)):
    errors.append(f"Feature IDs are not exactly 1..37: {ids}")

# 2) Every feature endpoint claimed by the capability registry is actually mounted.
routes={getattr(r,"path",None) for r in app.routes}

def route_exists(path: str) -> bool:
    if path in routes:
        return True
    # FastAPI stores parameterized endpoints as templates such as
    # /api/earth-engine/layer/{layer_id}; capability entries may intentionally
    # name a concrete layer such as /api/earth-engine/layer/dynamic_world_trees.
    for route in routes:
        if not route:
            continue
        pattern="^"+re.sub(r"\\{[^/]+\\}",r"[^/]+",re.escape(route).replace(r"\\{", "{").replace(r"\\}", "}"))+"$"
        # The escaped/template transform above is deliberately simple. If it
        # cannot produce a match, fall back to segment comparison.
        if re.match(pattern,path):
            return True
        rs=route.strip("/").split("/")
        ps=path.strip("/").split("/")
        if len(rs)==len(ps) and all(a==b or (a.startswith("{") and a.endswith("}")) for a,b in zip(rs,ps)):
            return True
    return False

for feat in FEATURE_CAPABILITIES:
    if not feat.get("endpoints"):
        errors.append(f"Feature {feat['id']} {feat['name']} has no runtime endpoint")
    for raw in feat.get("endpoints",[]):
        path=raw.split("?",1)[0]
        if not route_exists(path):
            errors.append(f"Feature {feat['id']} {feat['name']} references missing route {path}")

# 3) Every map-layer render mode has executable frontend handling.
js=(ROOT/"web/app.js").read_text(encoding="utf-8")
render_types={l.get("render") for g in LAYER_GROUPS for l in g.get("layers",[]) if l.get("render")}
for render in sorted(render_types):
    marker=f"def.render==='{render}'"
    if marker not in js:
        errors.append(f"Layer render mode {render!r} has no dashboard handler")

# 4) Every explicit dashboard button ID is wired in JavaScript.
html=(ROOT/"web/index.html").read_text(encoding="utf-8")
buttons=re.findall(r'<button[^>]*id="([^"]+)"',html)
for button_id in buttons:
    patterns=[
        f"$('{button_id}').onclick",
        f'$("#{button_id}")',
        f"getElementById('{button_id}')",
        f'getElementById("{button_id}")',
        f"$('{button_id}').addEventListener",
    ]
    if not any(p in js for p in patterns):
        errors.append(f"Dashboard button #{button_id} has no direct JS wiring")

# 5) Critical reference-dashboard sections remain present.
required_ids={
    "map","regionTitle","areaAffected","aiConfidence","ndviChange","riskScore",
    "sourceList","keyEvidence","causeBars","signalBars","compareShell",
    "reportBtn","patrolBtn","layersBtn","searchBtn",
    "dataModeBadge","dataIntegrityPanel","modelQualityPanel",
    "predictionWhat","predictionWhy","predictionActions","predictionImpact","predictionConfidence",
    "patrolRouteMap","patrolEvidenceFiles"
}
html_ids=set(re.findall(r'id="([^"]+)"',html))
for x in sorted(required_ids-html_ids):
    errors.append(f"Approved dashboard reference section #{x} is missing")

# 6) Production UI must not expose demo/synthetic scenario loaders.
for forbidden in ("demoScenarioSelect","loadDemoScenario","PRE-FLIGHT VERIFIED DEMO"):
    if forbidden in html or forbidden in js:
        errors.append(f"Production dashboard still exposes forbidden demo control/text: {forbidden}")

# 7) Critical live workflows must remain defined after UI refactors.
for fn in ("doSearch","generateReport","renderDataIntegrity","renderModelQuality","runPrediction","runPatrol","openAlertCenter"):
    if f"function {fn}" not in js and f"async function {fn}" not in js:
        errors.append(f"Critical live workflow function {fn} is missing")

# 8) What-if defaults must be neutral; hypothetical deltas cannot masquerade as observed data.
for input_id in ("whatTemp","whatRain","whatFire"):
    m=re.search(rf'id="{input_id}"[^>]*value="([^"]+)"',html)
    if not m or float(m.group(1))!=0:
        errors.append(f"Scenario input #{input_id} must default to zero in production")

if errors:
    print("VanRakshak acceptance check FAILED")
    for e in errors:
        print("-",e)
    raise SystemExit(1)

print("VanRakshak acceptance check PASSED")
print(f"- features: {len(FEATURE_CAPABILITIES)}/37")
print(f"- API routes: {len(routes)}")
print(f"- layer render modes wired: {len(render_types)}")
print(f"- explicit dashboard buttons wired: {len(buttons)}")
