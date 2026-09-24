from __future__ import annotations
from math import cos, radians
import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.warp import transform_bounds, reproject, Resampling, transform_geom
from rasterio.features import shapes
from scipy.ndimage import median_filter

class SARChangeError(RuntimeError):
    pass

def _bbox(lat: float, lon: float, radius_km: float):
    dlat=radius_km/111.32
    dlon=radius_km/max(20.0,111.32*cos(radians(lat)))
    return (lon-dlon,lat-dlat,lon+dlon,lat+dlat)

def _href(item: dict, asset: str):
    a=(item.get("assets") or {}).get(asset) or {}
    href=a.get("href")
    if not href:
        raise SARChangeError(f"Sentinel-1 item {item.get('id')} lacks {asset} asset")
    return href

def _window(src,bbox4326):
    b=transform_bounds("EPSG:4326",src.crs,*bbox4326,densify_pts=21)
    win=src.window(*b).round_offsets().round_lengths()
    full=Window(0,0,src.width,src.height)
    try: win=win.intersection(full)
    except Exception as exc: raise SARChangeError("AOI does not overlap Sentinel-1 scene") from exc
    if win.width<2 or win.height<2: raise SARChangeError("SAR AOI is too small")
    return win

def _read_reference(href,bbox4326):
    env={"GDAL_HTTP_MULTIRANGE":"YES","CPL_VSIL_CURL_ALLOWED_EXTENSIONS":".tif,.TIF"}
    with rasterio.Env(**env):
        with rasterio.open(href) as src:
            win=_window(src,bbox4326)
            arr=src.read(1,window=win).astype("float32")
            return arr,src.window_transform(win),src.crs

def _read_to_grid(href,bbox4326,shape,transform,crs):
    env={"GDAL_HTTP_MULTIRANGE":"YES","CPL_VSIL_CURL_ALLOWED_EXTENSIONS":".tif,.TIF"}
    with rasterio.Env(**env):
        with rasterio.open(href) as src:
            win=_window(src,bbox4326)
            arr=src.read(1,window=win).astype("float32")
            out=np.full(shape,np.nan,dtype="float32")
            reproject(
                arr,out,src_transform=src.window_transform(win),src_crs=src.crs,
                dst_transform=transform,dst_crs=crs,src_nodata=0,dst_nodata=np.nan,
                resampling=Resampling.bilinear,
            )
            return out

def _amplitude_db(arr):
    # Earth Search describes sentinel-1-grd as amplitude-only GRD measurement assets.
    x=np.where(np.isfinite(arr)&(arr>0),arr,np.nan)
    return 20.0*np.log10(np.maximum(x,1e-6))

def _props(item):
    p=item.get("properties") or {}
    return {
        "id":item.get("id"),
        "datetime":p.get("datetime"),
        "orbit_state":p.get("sat:orbit_state"),
        "relative_orbit":p.get("sat:relative_orbit") or p.get("sat:relative_orbit_number"),
        "polarizations":p.get("sar:polarizations"),
    }

def analyze(before: dict, after: dict, lat: float, lon: float, radius_km: float = 2.0, drop_db_threshold: float = 2.5):
    bbox4326=_bbox(lat,lon,max(.2,min(radius_km,8)))
    bvv,transform,crs=_read_reference(_href(before,"vv"),bbox4326)
    avv=_read_to_grid(_href(after,"vv"),bbox4326,bvv.shape,transform,crs)

    bvh=avh=None
    if "vh" in (before.get("assets") or {}) and "vh" in (after.get("assets") or {}):
        bvh=_read_to_grid(_href(before,"vh"),bbox4326,bvv.shape,transform,crs)
        avh=_read_to_grid(_href(after,"vh"),bbox4326,bvv.shape,transform,crs)

    bvv_db=median_filter(_amplitude_db(bvv),size=3,mode="nearest")
    avv_db=median_filter(_amplitude_db(avv),size=3,mode="nearest")
    dvv=avv_db-bvv_db
    valid=np.isfinite(dvv)

    dvh=None
    if bvh is not None and avh is not None:
        bvh_db=median_filter(_amplitude_db(bvh),size=3,mode="nearest")
        avh_db=median_filter(_amplitude_db(avh),size=3,mode="nearest")
        dvh=avh_db-bvh_db
        valid &= np.isfinite(dvh)

    if int(valid.sum())<50:
        raise SARChangeError("Too few valid Sentinel-1 pixels for SAR change screening")

    # Forest clearing often reduces cross-pol and/or co-pol return. This is a screening
    # threshold, not a universal physical classifier.
    candidate=valid&(dvv<=-abs(drop_db_threshold))
    if dvh is not None:
        candidate |= valid&(dvh<=-abs(drop_db_threshold))

    px_area=abs(float(transform.a*transform.e)) if crs and getattr(crs,"is_projected",False) else None
    area_ha=float(candidate.sum())*px_area/10000 if px_area else None
    feats=[]
    for geom,val in shapes(candidate.astype("uint8"),mask=candidate,transform=transform):
        if val!=1: continue
        try: g=transform_geom(crs,"EPSG:4326",geom,precision=6)
        except Exception: g=geom
        feats.append({"type":"Feature","properties":{"class":"sar_disturbance_candidate"},"geometry":g})
        if len(feats)>=250: break

    def stat(arr):
        return round(float(np.nanmedian(arr[valid])),3) if arr is not None else None

    fraction=float(candidate.sum()/valid.sum())
    magnitude=max(0.0,min(1.0,abs(min(0.0,stat(dvh) if dvh is not None else stat(dvv)))/6.0))
    confidence=max(0.0,min(.95,.55*magnitude+.45*min(1.0,fraction/.2)))
    return {
        "before":_props(before),"after":_props(after),
        "aoi_bbox":bbox4326,
        "valid_pixels":int(valid.sum()),
        "candidate_pixels":int(candidate.sum()),
        "candidate_fraction":round(fraction,5),
        "candidate_area_ha":round(area_ha,3) if area_ha is not None else None,
        "median_vv_change_db":stat(dvv),
        "median_vh_change_db":stat(dvh),
        "screening_confidence":round(confidence,3),
        "threshold_db":float(drop_db_threshold),
        "geojson":{"type":"FeatureCollection","features":feats},
        "label":"DERIVED_METRIC",
        "method":"Matched-orbit Sentinel-1 GRD VV/VH amplitude log-change with 3x3 median speckle screening",
        "warning":"This is measured SAR-change corroboration from GRD amplitude assets, not terrain-corrected field proof. Interpret with optical change, orbit geometry and land-cover context.",
    }
