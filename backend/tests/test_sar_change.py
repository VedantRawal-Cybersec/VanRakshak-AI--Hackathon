import numpy as np
from app.services import sar_change

def test_sar_amplitude_db_monotonic():
    a=np.array([1.0,10.0,100.0],dtype="float32")
    db=sar_change._amplitude_db(a)
    assert db[0] < db[1] < db[2]

def test_sar_bbox_contains_point():
    w,s,e,n=sar_change._bbox(12.3,75.8,2)
    assert w < 75.8 < e
    assert s < 12.3 < n

def test_feature_registry_exposes_sar_change():
    from app.services.feature_status import FEATURE_CAPABILITIES
    f=next(x for x in FEATURE_CAPABILITIES if x["id"]==3)
    assert "/api/analysis/sar-change" in f["endpoints"]


def test_s1_s3_asset_is_streamed_over_regional_https():
    href="s3://sentinel-s1-l1c/GRD/2025/11/5/IW/DV/example/measurement/iw-vv.tiff"
    out=sar_change._public_raster_href(href)
    assert out=="https://sentinel-s1-l1c.s3.eu-central-1.amazonaws.com/GRD/2025/11/5/IW/DV/example/measurement/iw-vv.tiff"


def test_s1_item_projection_metadata_builds_grid():
    class Src:
        width=100
        height=80
        crs=None
        transform=None
    item={"properties":{"proj:epsg":4326,"proj:shape":[80,100],"proj:transform":[0.001,0,75.0,0,-0.001,13.0]}}
    transform,crs=sar_change._item_grid(item,Src())
    assert crs.to_epsg()==4326
    assert transform.a==0.001
    assert transform.e==-0.001
