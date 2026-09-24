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
    transform,crs,grid_h,grid_w,transposed=sar_change._grid_layout(item,Src())
    assert crs.to_epsg()==4326
    assert transform.a==0.001
    assert transform.e==-0.001
    assert (grid_h,grid_w)==(80,100)
    assert transposed is False


def test_s1_projection_accepts_exact_transposed_archive_shape():
    class Src:
        width=25547
        height=16744
        crs=None
        transform=None
    item={"properties":{"proj:epsg":4326,"proj:shape":[25547,16744],"proj:transform":[0.0001,0,75.0,0,-0.0001,13.0]}}
    transform,crs,grid_h,grid_w,transposed=sar_change._grid_layout(item,Src())
    assert crs.to_epsg()==4326
    assert transform.a==0.0001
    assert (grid_h,grid_w)==(25547,16744)
    assert transposed is True


def test_s1_transposed_grid_maps_to_swapped_source_window():
    class Src:
        width=10
        height=20
        crs=None
        transform=None
    item={"properties":{"proj:epsg":4326,"proj:shape":[10,20],"proj:transform":[0.1,0,75.0,0,-0.1,13.0]}}
    src_win,grid_win,_,_,transposed=sar_change._grid_window(Src(),item,(75.2,12.5,75.8,12.8))
    assert transposed is True
    assert int(round(grid_win.width))==6
    assert int(round(grid_win.height))==3
    assert int(round(src_win.width))==3
    assert int(round(src_win.height))==6
