from __future__ import annotations
from io import BytesIO
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.features import shapes
from shapely.geometry import shape, mapping
from scipy.ndimage import label

class RasterInputError(ValueError): pass

def _read_red_nir(blob: bytes):
    with MemoryFile(blob) as mem:
        with mem.open() as ds:
            if ds.count < 2: raise RasterInputError("Expected a 2-band GeoTIFF: band 1 Red, band 2 NIR")
            red=ds.read(1).astype('float32'); nir=ds.read(2).astype('float32')
            return red,nir,ds.transform,ds.crs,ds.nodata

def _ndvi(red,nir):
    den=nir+red
    return np.divide(nir-red,den,out=np.zeros_like(den,dtype='float32'),where=np.abs(den)>1e-6)

def ndvi_change(before_blob:bytes, after_blob:bytes, threshold:float=.2):
    br,bn,transform,crs,_=_read_red_nir(before_blob); ar,an,t2,c2,_=_read_red_nir(after_blob)
    if br.shape!=ar.shape: raise RasterInputError("Before and after rasters must have the same dimensions")
    if transform!=t2: raise RasterInputError("Before and after rasters must be co-registered (same transform)")
    ndvi_b=_ndvi(br,bn); ndvi_a=_ndvi(ar,an); delta=ndvi_a-ndvi_b
    mask=(delta <= -abs(threshold)) & (ndvi_b > .3)
    px_area=abs(transform.a*transform.e)
    area_ha=float(mask.sum()*px_area/10000) if crs and getattr(crs,'is_projected',False) else None
    feats=[]
    for geom,val in shapes(mask.astype('uint8'),mask=mask,transform=transform):
        if val==1: feats.append({"type":"Feature","properties":{"change":"vegetation_loss"},"geometry":geom})
        if len(feats)>=300: break
    structure=np.ones((3,3),dtype=int); labeled,n=label(mask,structure=structure)
    sizes=np.bincount(labeled.ravel())[1:] if n else np.array([])
    return {
        "mean_ndvi_before":round(float(np.nanmean(ndvi_b)),4),
        "mean_ndvi_after":round(float(np.nanmean(ndvi_a)),4),
        "mean_ndvi_delta":round(float(np.nanmean(delta)),4),
        "loss_pixels":int(mask.sum()),
        "affected_area_ha":round(area_ha,3) if area_ha is not None else None,
        "patch_count":int(n),
        "largest_patch_pixels":int(sizes.max()) if sizes.size else 0,
        "threshold":threshold,
        "geojson":{"type":"FeatureCollection","features":feats},
        "crs":str(crs) if crs else None,
        "label":"DERIVED_METRIC",
        "notes":["Baseline NDVI-change detector; not a substitute for a trained deforestation model.","Area is only reported automatically when raster CRS is projected in linear units."]
    }
