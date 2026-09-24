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
