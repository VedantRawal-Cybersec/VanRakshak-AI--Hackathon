from io import BytesIO
from datetime import datetime, timezone
import numpy as np
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from app.adapters.earth_search import EarthSearchAdapter
from app.adapters.gfw import GFWAdapter
from app.models import ThreatPredictionRequest
from app.services.prediction import predict
from app.services.fragmentation import metrics


def test_earth_search_tile_spec_ndvi():
    item={
        "id":"S2_TEST",
        "bbox":[77,12,78,13],
        "properties":{"datetime":"2026-09-20T05:00:00Z","eo:cloud_cover":5},
        "links":[{"rel":"self","href":"https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2_TEST"}],
    }
    spec=EarthSearchAdapter().tile_spec(item,"ndvi")
    assert spec["mode"]=="ndvi"
    assert "assets=red" in spec["tile_url"]
    assert "assets=nir" in spec["tile_url"]
    from urllib.parse import parse_qs, urlparse
    assert parse_qs(urlparse(spec["tile_url"]).query)["expression"]==["(b2-b1)/(b2+b1)"]
    assert spec["resolution_m"]==10


def test_gfw_public_tile_template():
    spec=GFWAdapter().tile_layer("gfw_integrated_alerts", "2026-09-01", "2026-09-24", "high")
    assert "/gfw_integrated_alerts/latest/dynamic/" in spec["tile_url"]
    assert "start_date=2026-09-01" in spec["tile_url"]
    assert "alert_confidence=high" in spec["tile_url"]


def test_prediction_baseline():
    out=predict(ThreatPredictionRequest(values=[20,25,30,35],dates=["2026-01-01","2026-02-01","2026-03-01","2026-04-01"],steps=3))
    assert len(out["projected_values"])==3
    assert out["projected_values"][0] > 35
    assert len(out["forecast_dates"])==3
    assert out["analysis"]["direction"]=="INCREASING"
    assert out["analysis"]["confidence_pct"] >= 0
    assert out["diagnostics"]["models"]["theil_sen_robust"]["weight"] > 0
    assert out["label"]=="AI_ESTIMATE"


def _single_band_tif(arr):
    transform=from_origin(0,100,10,10)
    with MemoryFile() as mem:
        with mem.open(driver="GTiff",height=arr.shape[0],width=arr.shape[1],count=1,dtype="float32",crs="EPSG:32643",transform=transform) as ds:
            ds.write(arr.astype("float32"),1)
        return mem.read()


def test_fragmentation_metrics():
    a=np.zeros((10,10),dtype="float32")
    a[1:4,1:4]=1
    a[6:9,6:9]=1
    out=metrics(_single_band_tif(a),.5)
    assert out["patch_count"]==2
    assert out["forest_area_ha"]==0.18
    assert out["forest_fraction"]==0.18

def test_prediction_robust_to_single_outlier():
    out=predict(ThreatPredictionRequest(values=[20,21,22,90,24,25],steps=2,floor=0,ceiling=100))
    assert out["projected_values"][-1] < 60
    assert out["analysis"]["observations"]==6
    assert out["analysis"]["direction"] in {"INCREASING","STABLE"}


def test_patrol_priority_matrix_ordering():
    from app.models import PatrolRequest, PatrolPoint
    from app.services.patrol import optimize
    req=PatrolRequest(start_lat=12.0,start_lon=75.0,points=[
        PatrolPoint(id="near-low",lat=12.01,lon=75.01,priority=20),
        PatrolPoint(id="far-critical",lat=12.02,lon=75.02,priority=95),
    ])
    durations=[[0,300,360],[300,0,120],[360,120,0]]
    distances=[[0,2000,2500],[2000,0,900],[2500,900,0]]
    out=optimize(req,durations,distances)
    assert out["ordering_mode"]=="ROAD_TIME_PRIORITY"
    assert out["route"][0]["id"]=="far-critical"
    assert out["route"][0]["estimated_road_leg_min"]==6.0

def test_prediction_accepts_duplicate_day_observations():
    out=predict(ThreatPredictionRequest(
        values=[10,12,13,14],
        dates=["2026-01-01","2026-01-01","2026-02-01","2026-03-01"],
        steps=2,
    ))
    assert len(out["projected_values"])==2
    assert len(out["forecast_dates"])==2
    assert out["analysis"]["cadence_days"] > 0
