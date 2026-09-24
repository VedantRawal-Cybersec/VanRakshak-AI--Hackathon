from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_health():
    r=client.get('/api/health'); assert r.status_code==200 and r.json()['ok'] is True

def test_layers():
    r=client.get('/api/layers'); assert r.status_code==200 and len(r.json()['groups'])>=10

def test_features_37():
    r=client.get('/api/features'); assert r.json()['count']==37

def test_query_parser():
    r=client.get('/api/query',params={'q':'Show forests in Karnataka with high heat and recent canopy loss'}); assert r.status_code==200; assert r.json()['filters']['state']=='Karnataka'


def test_fallback_status():
    r=client.get('/api/fallbacks/status')
    assert r.status_code==200
    data=r.json()
    assert data['strategy']['fire']['credential_free_fallback'] is True
    assert data['strategy']['protected_areas']['credential_free_fallback'] is True

def test_gibs_catalog_and_tile_spec():
    r=client.get('/api/gibs/catalog')
    assert r.status_code==200 and r.json()['auth_required'] is False
    t=client.get('/api/gibs/layer/modis_terra_true_color',params={'date':'2026-09-20'})
    assert t.status_code==200
    assert '/wmts/epsg3857/best/' in t.json()['tile_url']

def test_feature_status_all_37_have_runtime_status():
    r=client.get('/api/features/status')
    assert r.status_code==200
    data=r.json()
    assert data['count']==37
    assert all(x.get('status') for x in data['features'])


def test_ready_endpoint():
    r=client.get('/api/ready')
    assert r.status_code==200
    assert r.json()['ok'] is True


def test_demo_scenarios_are_real_preflight_inputs():
    r=client.get('/api/demo-scenarios')
    assert r.status_code==200
    data=r.json()
    assert data['count']==5
    primaries=[x for x in data['scenarios'] if x['priority']=='PRIMARY']
    assert len(primaries)>=3
    assert all(x['sentinel2']['before']['id'] and x['sentinel2']['after']['id'] for x in primaries)
    assert all(x['sentinel1']['matched_pair'] is True for x in primaries)


def test_cache_status_reports_resilient_backend():
    r=client.get('/api/cache/status')
    assert r.status_code==200
    assert r.json()['persistent_backend']=='redis_with_memory_fallback'


def test_all_37_features_default_to_real_data_paths():
    r=client.get('/api/features/status')
    assert r.status_code==200
    data=r.json()
    assert data['count']==37
    assert all(x.get('real_data_default') is True for x in data['features'])
    assert all(x.get('data_mode') for x in data['features'])
    assert all(x.get('preferred_endpoint','').startswith('/api/') for x in data['features'])


def test_dashboard_uses_real_evidence_endpoints_for_core_actions():
    from pathlib import Path
    js_candidates=[Path('/web/app.js'),Path('web/app.js'),Path(__file__).resolve().parents[2]/'web'/'app.js']
    js=next(p for p in js_candidates if p.exists()).read_text(encoding='utf-8')
    assert '/api/query/live?' in js
    assert '/api/intelligence/predict-location?' in js
    assert '/api/intelligence/what-if-location?' in js
    assert '/api/patrol/live?' in js
    assert "/api/query?q=" not in js
    assert "api('/api/intelligence/predict'" not in js
    assert "api('/api/intelligence/what-if'" not in js
    assert "api('/api/patrol/road-route'" not in js


def test_dashboard_filters_drive_live_layer_requests():
    from pathlib import Path
    js_candidates=[Path('/web/app.js'),Path('web/app.js'),Path(__file__).resolve().parents[2]/'web'/'app.js']
    js=next(p for p in js_candidates if p.exists()).read_text(encoding='utf-8')
    assert "satelliteLayerPath" in js
    assert "start_date" in js and "end_date" in js
    assert "cloudFilter" in js and "confidenceFilter" in js
    assert "scheduleLayerFilterApply" in js and "applyLayerFilters" in js
    assert "['freshnessFilter','resolutionFilter','cloudFilter','confidenceFilter','startDate','endDate']" in js
    assert "mode=true_color&cloud_lt=60" not in js
    assert "mode=ndvi&cloud_lt=60" not in js


def test_satellite_render_probe_route_registered():
    paths={r.path for r in app.routes}
    assert '/api/map/satellite-modes/status' in paths


def test_gibs_keyless_environmental_wms_specs():
    for layer in ('viirs_snpp_true_color','viirs_snpp_thermal_anomalies','modis_terra_ndvi_8day','modis_terra_lst_day','imerg_precipitation_rate'):
        r=client.get('/api/gibs/layer/'+layer,params={'date':'2026-09-20'})
        assert r.status_code==200
        body=r.json()
        assert body['service']=='wms'
        assert '/wms/epsg3857/best/wms.cgi?' in body['tile_url']
        assert '{bbox-epsg-3857}' in body['tile_url']
        assert body['auth_required'] is False
