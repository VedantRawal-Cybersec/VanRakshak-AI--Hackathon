from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_health():
    r=client.get('/api/health'); assert r.status_code==200 and r.json()['ok'] is True


def test_health_head_and_favicon_routes_are_browser_clean():
    assert client.head('/api/health').status_code == 200
    fav=client.get('/favicon.ico')
    assert fav.status_code in {200,204}

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

def test_optional_earth_engine_rasters_return_public_fallbacks(monkeypatch):
    from app import main
    from app.adapters.base import AdapterError

    def unavailable(*args,**kwargs):
        raise AdapterError("Earth Engine intentionally unavailable in fallback test")

    monkeypatch.setattr(main.ee,"tile",unavailable)

    burned=client.get('/api/earth-engine/layer/modis_burned_area',params={'lat':12.3375,'lon':75.8069})
    assert burned.status_code==200
    b=burned.json()
    assert b['fallback_used'] is True
    assert b['tile_url']
    assert 'fire' in b['source'].lower()
    assert 'not MODIS MCD64A1' in b['fallback_semantics']

    lst=client.get('/api/earth-engine/layer/modis_lst',params={'lat':12.3375,'lon':75.8069})
    assert lst.status_code==200
    l=lst.json()
    assert l['fallback_used'] is True
    assert l['source']=='NASA Earthdata GIBS'
    assert '{bbox-epsg-3857}' in l['tile_url']

    water=client.get('/api/earth-engine/layer/jrc_water_occurrence',params={'lat':12.3375,'lon':75.8069})
    assert water.status_code==200
    w=water.json()
    assert w['fallback_used'] is True
    assert 'OPERA' in w['fallback_semantics']


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
    assert "source:'User-entered series'" in js
    assert "api('/api/intelligence/what-if'" not in js
    assert "$('patrolPoints').value.trim()" in js
    assert "renderPredictionResult" in js
    assert "renderPatrolResult" in js
    assert "predictionChart" in js
    assert "road travel matrix" in js


def test_dashboard_filters_drive_live_layer_requests():
    from pathlib import Path
    js_candidates=[Path('/web/app.js'),Path('web/app.js'),Path(__file__).resolve().parents[2]/'web'/'app.js']
    js=next(p for p in js_candidates if p.exists()).read_text(encoding='utf-8')
    assert "satelliteLayerPath" in js
    assert "start_date" in js and "end_date" in js
    assert "cloudFilter" in js and "confidenceFilter" in js
    assert "scheduleLayerFilterApply" in js and "applyLayerFilters" in js
    assert "['freshnessFilter','resolutionFilter','sourceFilter','renderFilter','cloudFilter','confidenceFilter','startDate','endDate']" in js
    assert "applyFilters" in js and "resetFilters" in js
    assert "satelliteModeQuick" in js
    assert "days:'90'" in js
    assert "maxzoom" in js
    assert ";$$('[data-layer]').forEach" in js
    assert ";$('[data-layer]').forEach" not in js
    assert "mode=true_color&cloud_lt=60" not in js
    assert "mode=ndvi&cloud_lt=60" not in js


def test_satellite_render_probe_route_registered():
    paths={r.path for r in app.routes}
    assert '/api/map/satellite-modes/status' in paths


def test_gibs_keyless_environmental_wms_specs():
    for layer in ('viirs_snpp_true_color','viirs_snpp_thermal_anomalies','modis_terra_ndvi_8day','modis_terra_lst_day','imerg_precipitation_rate','opera_dist_alert_hls','opera_surface_water_hls','smap_soil_moisture'):
        r=client.get('/api/gibs/layer/'+layer,params={'date':'2026-09-20'})
        assert r.status_code==200
        body=r.json()
        assert body['service']=='wms'
        assert '/wms/epsg3857/best/wms.cgi?' in body['tile_url']
        assert '{bbox-epsg-3857}' in body['tile_url']
        assert body['auth_required'] is False


def test_open_source_integration_registry():
    r=client.get('/api/integrations/open-source')
    assert r.status_code==200
    data=r.json()
    assert data['count']>=8
    repos={x['repo'] for x in data['integrations']}
    assert 'developmentseed/titiler' in repos
    assert 'stac-utils/pystac-client' in repos
    assert 'microsoft/planetary-computer-sdk-for-python' in repos
    assert 'earthaccess-dev/earthaccess' in repos
    assert 'opendatacube/odc-stac' in repos


def test_dashboard_has_no_hidden_global_date_filter():
    from pathlib import Path
    js_candidates=[Path('/web/app.js'),Path('web/app.js'),Path(__file__).resolve().parents[2]/'web'/'app.js']
    js=next(p for p in js_candidates if p.exists()).read_text(encoding='utf-8')
    assert "['startDate','endDate'].forEach(id=>{if($(id))$(id).value=''});" in js
    assert "satelliteModeQuick" in js
    assert "sourceFilter" in js and "renderFilter" in js



def test_live_patrol_no_hotspots_is_valid_analysis(monkeypatch):
    from app import main
    async def fake_evidence(*args,**kwargs):
        return {
            "change":{
                "geojson":{"type":"FeatureCollection","features":[]},
                "candidate_area_ha":0,
                "screening_confidence":0.12,
                "before":{"id":"before","datetime":"2025-11-06T00:00:00Z"},
                "after":{"id":"after","datetime":"2026-02-04T00:00:00Z"},
            },
            "warning":{"score":18},
        }
    monkeypatch.setattr(main,"evidence_chain_ep",fake_evidence)
    r=client.get("/api/patrol/live",params={
        "lat":12.3375,"lon":75.8069,"place":"Kodagu",
        "before_date":"2025-11-06","after_date":"2026-02-04",
    })
    assert r.status_code==200
    data=r.json()
    assert data["status"]=="NO_PATROL_TARGETS"
    assert data["ordering"]["route"]==[]
    assert data["route_summary"]["stops"]==0


def test_predict_location_returns_operational_forecast_intelligence(monkeypatch):
    from app import main

    async def fake_series(*args, **kwargs):
        return {
            "observations": [
                {"datetime":"2026-01-01T05:00:00Z","mean_ndvi":0.72,"forest_fraction":0.82,"cloud_masked_fraction":0.08,"id":"S1"},
                {"datetime":"2026-02-01T05:00:00Z","mean_ndvi":0.69,"forest_fraction":0.80,"cloud_masked_fraction":0.10,"id":"S2"},
                {"datetime":"2026-03-01T05:00:00Z","mean_ndvi":0.61,"forest_fraction":0.74,"cloud_masked_fraction":0.07,"id":"S3"},
                {"datetime":"2026-04-01T05:00:00Z","mean_ndvi":0.54,"forest_fraction":0.67,"cloud_masked_fraction":0.09,"id":"S4"},
            ],
            "errors": [],
            "source": "Sentinel-2 test series",
        }

    monkeypatch.setattr(main, "vegetation_series_ep", fake_series)
    r=client.get("/api/intelligence/predict-location", params={
        "lat":12.3375,
        "lon":75.8069,
        "start":"2026-01-01",
        "end":"2026-04-30",
        "max_observations":12,
    })
    assert r.status_code==200
    data=r.json()
    fi=data["forecast_intelligence"]
    assert fi["what_is_happening"]
    assert len(fi["why_model_is_flagging_it"]) >= 4
    assert len(fi["recommended_actions"]) >= 3
    assert len(fi["expected_impacts"]) >= 4
    assert "probability" in fi["uncertainty"]["note"].lower()
    assert "cause" in fi["causation_note"].lower()


def test_live_patrol_returns_practical_field_evidence_brief(monkeypatch):
    from app import main

    async def fake_evidence(*args, **kwargs):
        return {
            "change":{
                "candidate_area_ha":2.4,
                "screening_confidence":0.84,
                "before":{"id":"S2_BEFORE","datetime":"2026-01-01T05:00:00Z","cloud_cover":5},
                "after":{"id":"S2_AFTER","datetime":"2026-02-01T05:00:00Z","cloud_cover":7},
                "geojson":{
                    "type":"FeatureCollection",
                    "features":[{
                        "type":"Feature",
                        "properties":{"area_ha":2.4},
                        "geometry":{"type":"Polygon","coordinates":[[[75.80,12.33],[75.81,12.33],[75.81,12.34],[75.80,12.34],[75.80,12.33]]]}
                    }]
                }
            },
            "warning":{"score":68},
            "forest_doctor":{"probable_drivers":[{"driver":"Road-access pressure","relative_support_pct":61}]},
            "action_plan":{"actions":[{"priority":"HIGH","what":"Ground verify","how":"Inspect the candidate polygon.","timeframe":"Within 24 h"}]},
        }

    async def fake_route(req):
        return {
            "ordering":{
                "route":[{"id":"candidate-1","lat":12.335,"lon":75.805,"priority":80,"priority_band":"HIGH","why_selected":"Largest candidate polygon","order":1}],
                "stop_count":1,
                "ordering_mode":"ROAD_TIME_PRIORITY"
            },
            "road_route":{
                "distance_km":4.2,
                "duration_min":13.0,
                "source":"OSRM / OpenStreetMap",
                "geometry":{"type":"LineString","coordinates":[[75.8069,12.3375],[75.805,12.335]]},
                "legs":[]
            },
            "status":"ROAD_ROUTE_READY"
        }

    monkeypatch.setattr(main, "evidence_chain_ep", fake_evidence)
    monkeypatch.setattr(main, "patrol_road_route", fake_route)
    r=client.get("/api/patrol/live", params={
        "lat":12.3375,"lon":75.8069,"place":"Kodagu",
        "before_date":"2026-01-01","after_date":"2026-02-01","max_points":5
    })
    assert r.status_code==200
    data=r.json()
    brief=data["operational_brief"]
    assert brief["before_scene"]["id"]=="S2_BEFORE"
    assert brief["after_scene"]["id"]=="S2_AFTER"
    assert any("video" in x.lower() for x in brief["evidence_required"])
    assert any("photo" in x.lower() for x in brief["evidence_required"])
    stop=data["ordering"]["route"][0]
    assert len(stop["field_tasks"]) >= 4
    assert "video" in stop["evidence_required"]
    assert data["road_route"]["geometry"]["type"]=="LineString"


def test_predict_location_temporal_backtest_uses_real_holdout_contract(monkeypatch):
    from app import main

    async def fake_series(*args, **kwargs):
        vals=[
            ("2026-01-01T05:00:00Z",0.76,0.84),
            ("2026-02-01T05:00:00Z",0.74,0.83),
            ("2026-03-01T05:00:00Z",0.72,0.81),
            ("2026-04-01T05:00:00Z",0.69,0.79),
            ("2026-05-01T05:00:00Z",0.65,0.75),
            ("2026-06-01T05:00:00Z",0.61,0.71),
            ("2026-07-01T05:00:00Z",0.58,0.68),
            ("2026-08-01T05:00:00Z",0.55,0.65),
        ]
        return {
            "observations":[
                {"datetime":d,"mean_ndvi":nd,"forest_fraction":fc,"cloud_masked_fraction":0.08,"id":f"S{i+1}"}
                for i,(d,nd,fc) in enumerate(vals)
            ],
            "errors":[],
            "source":"Sentinel-2 test series",
        }

    monkeypatch.setattr(main,"vegetation_series_ep",fake_series)
    r=client.get("/api/intelligence/predict-location",params={
        "lat":12.3375,"lon":75.8069,"start":"2026-01-01","end":"2026-08-31","max_observations":12,
    })
    assert r.status_code==200
    data=r.json()
    bt=data["analysis"]["temporal_backtest"]
    assert bt["available"] is True
    assert bt["validation_class"]=="REAL_SENTINEL_TEMPORAL_HOLDOUT"
    assert bt["holdout_observations"]>=2
    assert bt["mae"]>=0
    assert bt["rmse"]>=0
    assert 0 <= bt["interval_coverage_pct"] <= 100
    assert "ground-truth" in bt["note"].lower()
