from app.services.remote_change import _bbox

def test_bbox_reasonable():
    b=_bbox(12.9,77.5,2)
    assert b[0] < 77.5 < b[2]
    assert b[1] < 12.9 < b[3]
    assert (b[3]-b[1]) < 0.1
