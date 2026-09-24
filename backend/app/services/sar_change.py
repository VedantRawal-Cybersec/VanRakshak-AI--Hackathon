from __future__ import annotations
from math import cos, radians
from urllib.parse import quote
import numpy as np
import rasterio
from affine import Affine
from rasterio.crs import CRS
from rasterio.windows import Window, from_bounds
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
    return _public_raster_href(href)

def _public_raster_href(href: str) -> str:
    """Avoid GDAL /vsis3 dependency by streaming AWS Open Data COGs over HTTPS."""
    if not href.startswith("s3://"):
        return href
    rest=href[5:]
    bucket,sep,key=rest.partition("/")
    if not sep or not bucket or not key:
        raise SARChangeError(f"Malformed S3 raster URL: {href}")
    # Sentinel-1 GRD Open Data is hosted in eu-central-1. The regional endpoint
    # avoids S3 redirect/signing ambiguity and works with GDAL's /vsicurl path.
    if bucket=="sentinel-s1-l1c":
        host=f"{bucket}.s3.eu-central-1.amazonaws.com"
    else:
        host=f"{bucket}.s3.amazonaws.com"
    return f"https://{host}/{quote(key,safe='/._-')}"

def _item_grid(item: dict, src) -> tuple[Affine, CRS]:
    p=item.get("properties") or {}
    epsg=p.get("proj:epsg")
    raw_transform=p.get("proj:transform")
    raw_shape=p.get("proj:shape")
    if epsg and raw_transform and len(raw_transform)>=6:
        transform=Affine(*[float(x) for x in raw_transform[:6]])
        crs=CRS.from_epsg(int(epsg))
        if raw_shape and len(raw_shape)>=2:
            d0,d1=int(raw_shape[0]),int(raw_shape[1])
            direct=abs(src.height-d0)<=2 and abs(src.width-d1)<=2
            transposed=abs(src.width-d0)<=2 and abs(src.height-d1)<=2
            # Earth Search Sentinel-1 items in the archive are not fully uniform:
            # most follow STAC [rows, cols], while some historical/new items expose
            # the same two dimensions in [width, height] order. The affine transform
            # remains x/y ordered, so either exact orientation is safe; anything else
            # is rejected to avoid silent geolocation errors.
            if not (direct or transposed):
                raise SARChangeError(
                    f"Sentinel-1 projection metadata/raster shape mismatch: "
                    f"STAC dimensions {d0}x{d1}, raster {src.width}x{src.height}"
                )
        return transform,crs
    if src.crs and src.transform:
        return src.transform,src.crs
    raise SARChangeError("Sentinel-1 scene lacks usable projection metadata")

def _window(src,item,bbox4326):
    transform,crs=_item_grid(item,src)
    b=transform_bounds("EPSG:4326",crs,*bbox4326,densify_pts=21)
    win=from_bounds(*b,transform=transform).round_offsets().round_lengths()
    full=Window(0,0,src.width,src.height)
    try:
        win=win.intersection(full)
    except Exception as exc:
        raise SARChangeError("AOI does not overlap Sentinel-1 scene") from exc
    if win.width<2 or win.height<2:
        raise SARChangeError("SAR AOI is too small")
    return win,transform,crs

def _raster_env():
    return {
        "GDAL_HTTP_MULTIRANGE":"YES",
        "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES":"YES",
        "GDAL_DISABLE_READDIR_ON_OPEN":"EMPTY_DIR",
        "CPL_VSIL_CURL_USE_HEAD":"NO",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS":".tif,.TIF,.tiff,.TIFF",
    }

def _read_reference(item,asset,bbox4326):
    href=_href(item,asset)
    with rasterio.Env(**_raster_env()):
        with rasterio.open(href) as src:
            win,grid_transform,crs=_window(src,item,bbox4326)
            arr=src.read(1,window=win).astype("float32")
            return arr,rasterio.windows.transform(win,grid_transform),crs

def _read_to_grid(item,asset,bbox4326,shape,transform,crs):
    href=_href(item,asset)
    with rasterio.Env(**_raster_env()):
        with rasterio.open(href) as src:
            win,grid_transform,src_crs=_window(src,item,bbox4326)
            arr=src.read(1,window=win).astype("float32")
            out=np.full(shape,np.nan,dtype="float32")
            reproject(
                arr,out,src_transform=rasterio.windows.transform(win,grid_transform),src_crs=src_crs,
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
    bvv,transform,crs=_read_reference(before,"vv",bbox4326)
    avv=_read_to_grid(after,"vv",bbox4326,bvv.shape,transform,crs)

    bvh=avh=None
    if "vh" in (before.get("assets") or {}) and "vh" in (after.get("assets") or {}):
        bvh=_read_to_grid(before,"vh",bbox4326,bvv.shape,transform,crs)
        avh=_read_to_grid(after,"vh",bbox4326,bvv.shape,transform,crs)

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
    if px_area is None and crs and crs.to_epsg()==4326:
        # Approximate geographic pixel area at the AOI latitude for reporting only.
        metres_per_degree_lat=111_320.0
        metres_per_degree_lon=111_320.0*cos(radians(lat))
        px_area=abs(float(transform.a*transform.e))*metres_per_degree_lat*metres_per_degree_lon
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
        "method":"Matched-orbit Sentinel-1 GRD VV/VH amplitude log-change using Earth Search STAC projection metadata with 3x3 median speckle screening",
        "warning":"This is measured SAR-change corroboration from GRD amplitude assets, not terrain-corrected or radiometrically calibrated field proof. Interpret with optical change, orbit geometry and land-cover context.",
    }
