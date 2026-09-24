from rasterio.io import MemoryFile
from rasterio.transform import from_origin
import numpy as np
from app.services.raster_analysis import ndvi_change

def tif(red,nir):
    profile={"driver":"GTiff","height":red.shape[0],"width":red.shape[1],"count":2,"dtype":"float32","crs":"EPSG:32643","transform":from_origin(500000,1500000,10,10)}
    with MemoryFile() as mem:
        with mem.open(**profile) as ds:
            ds.write(red.astype('float32'),1); ds.write(nir.astype('float32'),2)
        return mem.read()

def test_ndvi_change_detects_loss():
    red=np.full((8,8),.1); nir=np.full((8,8),.8)
    red2=red.copy(); nir2=nir.copy(); red2[2:5,2:5]=.4; nir2[2:5,2:5]=.2
    out=ndvi_change(tif(red,nir),tif(red2,nir2),.2)
    assert out['loss_pixels']>=9
    assert out['affected_area_ha']>0
    assert out['patch_count']>=1
