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
