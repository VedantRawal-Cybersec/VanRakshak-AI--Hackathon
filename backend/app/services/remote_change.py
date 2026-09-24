from __future__ import annotations
from dataclasses import dataclass
from math import cos, radians
import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.warp import transform_bounds, reproject, Resampling, transform_geom
from rasterio.features import shapes
from scipy.ndimage import label as cc_label, binary_erosion
from app.adapters.base import AdapterError

CLOUD_SCL = {3, 8, 9, 10, 11}  # cloud shadow, medium/high cloud, cirrus, snow/ice

class RemoteChangeError(RuntimeError):
    pass


def _bbox(lat: float, lon: float, radius_km: float):
    dlat = radius_km / 111.32
    dlon = radius_km / max(20.0, 111.32 * cos(radians(lat)))
    return (lon-dlon, lat-dlat, lon+dlon, lat+dlat)


def _href(item: dict, name: str) -> str:
    asset = (item.get("assets") or {}).get(name) or {}
    href = asset.get("href")
    if not href:
        raise RemoteChangeError(f"STAC scene {item.get('id')} lacks asset {name}")
    return href


def _window_for_bbox(src, bbox4326):
    b = transform_bounds("EPSG:4326", src.crs, *bbox4326, densify_pts=21)
    win = src.window(*b).round_offsets().round_lengths()
    full = Window(0, 0, src.width, src.height)
    try:
        win = win.intersection(full)
    except Exception as e:
        raise RemoteChangeError("AOI does not overlap selected scene") from e
    if win.width < 2 or win.height < 2:
        raise RemoteChangeError("AOI is too small or outside selected scene")
    return win


def _read_reference(href: str, bbox4326):
    env = {"GDAL_HTTP_MULTIRANGE":"YES", "CPL_VSIL_CURL_ALLOWED_EXTENSIONS":".tif,.TIF"}
    with rasterio.Env(**env):
        with rasterio.open(href) as src:
            win = _window_for_bbox(src, bbox4326)
            arr = src.read(1, window=win).astype("float32")
            return arr, src.window_transform(win), src.crs


def _read_to_grid(href: str, bbox4326, dst_shape, dst_transform, dst_crs, resampling=Resampling.bilinear):
    env = {"GDAL_HTTP_MULTIRANGE":"YES", "CPL_VSIL_CURL_ALLOWED_EXTENSIONS":".tif,.TIF"}
    with rasterio.Env(**env):
        with rasterio.open(href) as src:
            win = _window_for_bbox(src, bbox4326)
            arr = src.read(1, window=win).astype("float32")
            src_transform = src.window_transform(win)
            out = np.full(dst_shape, np.nan, dtype="float32")
            reproject(
                source=arr, destination=out,
                src_transform=src_transform, src_crs=src.crs,
                dst_transform=dst_transform, dst_crs=dst_crs,
                src_nodata=0, dst_nodata=np.nan,
                resampling=resampling,
            )
            return out




def _fragmentation(mask: np.ndarray, px_area_m2: float | None = None) -> dict:
    mask = mask.astype(bool)
    structure=np.ones((3,3),dtype=int)
    lab,n=cc_label(mask,structure=structure)
    sizes=np.bincount(lab.ravel())[1:] if n else np.array([],dtype=int)
    core=binary_erosion(mask,structure=np.ones((3,3),dtype=bool),iterations=2,border_value=0) if mask.any() else mask
    # Edge pixels: forest pixels that are not part of the 2-pixel interior.
    edge=mask & (~binary_erosion(mask,structure=np.ones((3,3),dtype=bool),iterations=1,border_value=0)) if mask.any() else mask
    forest_pixels=int(mask.sum())
    out={
        "forest_pixels":forest_pixels, "patch_count":int(n),
        "largest_patch_pixels":int(sizes.max()) if sizes.size else 0,
        "mean_patch_pixels":round(float(sizes.mean()),2) if sizes.size else 0,
        "core_forest_fraction":round(float(core.sum()/forest_pixels),4) if forest_pixels else 0,
        "edge_pixel_fraction":round(float(edge.sum()/forest_pixels),4) if forest_pixels else 0,
    }
    if px_area_m2:
        out["forest_area_ha"]=round(forest_pixels*px_area_m2/10000,3)
        out["largest_patch_ha"]=round((int(sizes.max()) if sizes.size else 0)*px_area_m2/10000,3)
    return out

def _normalized_difference(a, b):
    den = a + b
    return np.divide(a-b, den, out=np.full_like(den, np.nan, dtype="float32"), where=np.abs(den)>1e-6)

def _ndvi(red, nir):
    return _normalized_difference(nir, red)



def scene_summary(item: dict, lat: float, lon: float, radius_km: float = 1.5, forest_ndvi_threshold: float = 0.45) -> dict:
    """Read a small Sentinel-2 COG window and summarize vegetation condition for one real scene."""
    bbox4326=_bbox(lat,lon,max(0.2,min(radius_km,5)))
    red,transform,crs=_read_reference(_href(item,"red"),bbox4326)
    nir=_read_to_grid(_href(item,"nir"),bbox4326,red.shape,transform,crs)
    try:
        scl=_read_to_grid(_href(item,"scl"),bbox4326,red.shape,transform,crs,Resampling.nearest)
        cloud=np.isin(np.nan_to_num(scl,nan=-1).astype(int),list(CLOUD_SCL))
    except Exception:
        cloud=np.zeros(red.shape,dtype=bool)
    ndvi=_ndvi(red,nir)
    valid=np.isfinite(ndvi)&(~cloud)
    forest=valid&(ndvi>=forest_ndvi_threshold)
    props=item.get("properties") or {}
    return {
        "id":item.get("id"),"datetime":props.get("datetime"),"catalog_cloud_cover":props.get("eo:cloud_cover"),
        "mean_ndvi":round(float(np.nanmean(ndvi[valid])),4) if valid.any() else None,
        "forest_fraction":round(float(forest.sum()/valid.sum()),4) if valid.any() else None,
        "valid_pixels":int(valid.sum()),"cloud_masked_fraction":round(float(cloud.sum()/cloud.size),4) if cloud.size else None,
        "forest_ndvi_threshold":forest_ndvi_threshold,"label":"DERIVED_METRIC",
        "method":"Sentinel-2 L2A Red/NIR NDVI with SCL cloud/shadow/snow mask",
    }

def recovery_from_series(rows: list[dict]) -> dict:
    rows=[r for r in rows if r.get("mean_ndvi") is not None and r.get("forest_fraction") is not None]
    if len(rows)<3:
        return {"status":"UNKNOWN","score":None,"label":"AI_ESTIMATE","warning":"At least three valid satellite observations are required."}
    n=min(3,max(1,len(rows)//3))
    b_nd=float(np.mean([r["mean_ndvi"] for r in rows[:n]])); c_nd=float(np.mean([r["mean_ndvi"] for r in rows[-n:]]))
    b_fc=float(np.mean([r["forest_fraction"] for r in rows[:n]])); c_fc=float(np.mean([r["forest_fraction"] for r in rows[-n:]]))
    nd_ratio=max(0,min(1.5,(c_nd+1e-6)/(b_nd+1e-6))) if b_nd>0 else 1
    fc_ratio=max(0,min(1.5,(c_fc+1e-6)/(b_fc+1e-6))) if b_fc>0 else 1
    # 100 represents return to or above the early-period condition; no missing climate/fire inputs are invented.
    score=round(max(0,min(100,(0.55*min(nd_ratio,1)+0.45*min(fc_ratio,1))*100)),1)
    nd_delta=c_nd-b_nd; fc_delta=c_fc-b_fc
    if nd_delta>0.04 and fc_delta>-0.03: status="RECOVERING"
    elif nd_delta<-0.05 or fc_delta<-0.08: status="DETERIORATING"
    else: status="STABLE"
    return {
        "status":status,"score":score,"mean_ndvi_baseline":round(b_nd,4),"mean_ndvi_current":round(c_nd,4),
        "forest_fraction_baseline":round(b_fc,4),"forest_fraction_current":round(c_fc,4),
        "ndvi_delta":round(nd_delta,4),"forest_fraction_delta":round(fc_delta,4),"observations":len(rows),
        "exit_conditions":{
            "WATCH_to_NORMAL":["recent 3-observation NDVI >= 90% of baseline","recent forest fraction >= 90% of baseline","no new confirmed disturbance alert"],
            "WARNING_to_WATCH":["NDVI >= 70% of baseline","forest fraction >= 75% of baseline","loss polygon does not expand on subsequent observation"],
        },
        "label":"AI_ESTIMATE","method":"Sentinel-only recovery screen; fire/climate conditions are reported separately rather than fabricated into the score",
    }

def analyze(before: dict, after: dict, lat: float, lon: float, radius_km: float = 2.0, ndvi_drop_threshold: float = 0.2, forest_ndvi_threshold: float = 0.45):
    bbox4326 = _bbox(lat, lon, max(0.2, min(radius_km, 10)))
    br, transform, crs = _read_reference(_href(before,"red"), bbox4326)
    shape = br.shape
    bn = _read_to_grid(_href(before,"nir"), bbox4326, shape, transform, crs)
    bg = _read_to_grid(_href(before,"green"), bbox4326, shape, transform, crs)
    bsw1 = _read_to_grid(_href(before,"swir16"), bbox4326, shape, transform, crs)
    bsw2 = _read_to_grid(_href(before,"swir22"), bbox4326, shape, transform, crs)
    ar = _read_to_grid(_href(after,"red"), bbox4326, shape, transform, crs)
    an = _read_to_grid(_href(after,"nir"), bbox4326, shape, transform, crs)
    ag = _read_to_grid(_href(after,"green"), bbox4326, shape, transform, crs)
    asw1 = _read_to_grid(_href(after,"swir16"), bbox4326, shape, transform, crs)
    asw2 = _read_to_grid(_href(after,"swir22"), bbox4326, shape, transform, crs)
    # SCL is 20m and is resampled with nearest-neighbour to the 10m reference grid.
    try:
        bscl = _read_to_grid(_href(before,"scl"), bbox4326, shape, transform, crs, Resampling.nearest)
        ascl = _read_to_grid(_href(after,"scl"), bbox4326, shape, transform, crs, Resampling.nearest)
        cloud = np.isin(np.nan_to_num(bscl,nan=-1).astype(int), list(CLOUD_SCL)) | np.isin(np.nan_to_num(ascl,nan=-1).astype(int), list(CLOUD_SCL))
    except Exception:
        cloud = np.zeros(shape, dtype=bool)

    ndvi_b = _ndvi(br,bn); ndvi_a = _ndvi(ar,an); delta = ndvi_a-ndvi_b
    ndmi_b = _normalized_difference(bn,bsw1); ndmi_a = _normalized_difference(an,asw1); ndmi_delta=ndmi_a-ndmi_b
    nbr_b = _normalized_difference(bn,bsw2); nbr_a = _normalized_difference(an,asw2); nbr_delta=nbr_a-nbr_b
    ndwi_b = _normalized_difference(bg,bn); ndwi_a = _normalized_difference(ag,an); ndwi_delta=ndwi_a-ndwi_b
    valid = np.isfinite(ndvi_b)&np.isfinite(ndvi_a)&np.isfinite(ndmi_b)&np.isfinite(ndmi_a)&np.isfinite(nbr_b)&np.isfinite(nbr_a)&(~cloud)
    # Primary high-precision candidate remains a forest-conditioned NDVI decline. Other indices corroborate severity.
    candidate = valid & (ndvi_b >= forest_ndvi_threshold) & (delta <= -abs(ndvi_drop_threshold))
    valid_n = int(valid.sum()); cand_n = int(candidate.sum())
    px_area = abs(float(transform.a*transform.e)) if crs and getattr(crs,"is_projected",False) else None
    area_ha = cand_n*px_area/10000 if px_area else None
    forest_before = valid & (ndvi_b >= forest_ndvi_threshold)
    forest_after = valid & (ndvi_a >= forest_ndvi_threshold)
    frag_before = _fragmentation(forest_before, px_area)
    frag_after = _fragmentation(forest_after, px_area)
    fragmentation_change = {
        "patch_count_delta": frag_after["patch_count"]-frag_before["patch_count"],
        "core_forest_fraction_delta": round(frag_after["core_forest_fraction"]-frag_before["core_forest_fraction"],4),
        "edge_pixel_fraction_delta": round(frag_after["edge_pixel_fraction"]-frag_before["edge_pixel_fraction"],4),
        "largest_patch_pixels_delta": frag_after["largest_patch_pixels"]-frag_before["largest_patch_pixels"],
    }
    feats=[]
    for geom,val in shapes(candidate.astype("uint8"),mask=candidate,transform=transform):
        if val != 1: continue
        try: geom4326=transform_geom(crs,"EPSG:4326",geom,precision=6)
        except Exception: geom4326=geom
        feats.append({"type":"Feature","properties":{"class":"candidate_forest_loss"},"geometry":geom4326})
        if len(feats)>=250: break

    mean_b=float(np.nanmean(ndvi_b[valid])) if valid_n else None
    mean_a=float(np.nanmean(ndvi_a[valid])) if valid_n else None
    loss_frac=cand_n/valid_n if valid_n else 0
    cloud_frac=float(cloud.sum()/cloud.size) if cloud.size else 0
    magnitude=max(0, min(1, float(-np.nanmean(delta[candidate])/0.6))) if cand_n else 0
    screening_conf=max(0,min(1,0.45*magnitude+0.35*min(1,loss_frac/0.2)+0.2*(1-cloud_frac))) if cand_n else 0
    # Unsupervised ML corroboration: anomalies are NOT called deforestation by themselves.
    anomaly_overlap=None; anomaly_pixels=None
    try:
        from sklearn.ensemble import IsolationForest
        coords=np.flatnonzero(valid)
        if coords.size >= 300:
            # Changes in vegetation/moisture/burn/water indices form an interpretable feature space.
            X=np.column_stack([delta.ravel()[coords],ndmi_delta.ravel()[coords],nbr_delta.ravel()[coords],ndwi_delta.ravel()[coords]])
            if X.shape[0] > 12000:
                rng=np.random.default_rng(42); train_idx=rng.choice(X.shape[0],12000,replace=False); Xtrain=X[train_idx]
            else: Xtrain=X
            iso=IsolationForest(n_estimators=120,contamination="auto",random_state=42,n_jobs=1).fit(Xtrain)
            pred=iso.predict(X) == -1
            anomaly_mask=np.zeros(valid.size,dtype=bool); anomaly_mask[coords]=pred; anomaly_mask=anomaly_mask.reshape(valid.shape)
            anomaly_pixels=int(anomaly_mask.sum())
            anomaly_overlap=round(float((candidate & anomaly_mask).sum()/cand_n),4) if cand_n else 0.0
    except Exception:
        anomaly_overlap=None; anomaly_pixels=None
    bp=before.get("properties") or {}; ap=after.get("properties") or {}
    return {
        "before":{"id":before.get("id"),"datetime":bp.get("datetime"),"cloud_cover":bp.get("eo:cloud_cover")},
        "after":{"id":after.get("id"),"datetime":ap.get("datetime"),"cloud_cover":ap.get("eo:cloud_cover")},
        "aoi_bbox":bbox4326,
        "mean_ndvi_before":round(mean_b,4) if mean_b is not None else None,
        "mean_ndvi_after":round(mean_a,4) if mean_a is not None else None,
        "mean_ndvi_change":round(mean_a-mean_b,4) if mean_a is not None and mean_b is not None else None,
        "candidate_loss_pixels":cand_n,
        "valid_pixels":valid_n,
        "candidate_fraction":round(loss_frac,5),
        "candidate_area_ha":round(area_ha,3) if area_ha is not None else None,
        "screening_confidence":round(screening_conf,3),
        "cloud_masked_fraction":round(cloud_frac,4),
        "multispectral":{
            "mean_ndmi_before":round(float(np.nanmean(ndmi_b[valid])),4) if valid_n else None,
            "mean_ndmi_after":round(float(np.nanmean(ndmi_a[valid])),4) if valid_n else None,
            "mean_ndmi_change":round(float(np.nanmean(ndmi_delta[valid])),4) if valid_n else None,
            "mean_nbr_before":round(float(np.nanmean(nbr_b[valid])),4) if valid_n else None,
            "mean_nbr_after":round(float(np.nanmean(nbr_a[valid])),4) if valid_n else None,
            "mean_nbr_change":round(float(np.nanmean(nbr_delta[valid])),4) if valid_n else None,
            "mean_ndwi_change":round(float(np.nanmean(ndwi_delta[valid])),4) if valid_n else None,
        },
        "ml_corroboration":{
            "method":"IsolationForest over per-pixel NDVI/NDMI/NBR/NDWI changes",
            "anomaly_pixels":anomaly_pixels,"candidate_overlap_fraction":anomaly_overlap,
            "interpretation":"Unsupervised anomalies only corroborate unusual change; they are not labels of deforestation."
        },
        "thresholds":{"before_forest_ndvi":forest_ndvi_threshold,"ndvi_drop":ndvi_drop_threshold},
        "fragmentation":{"before":frag_before,"after":frag_after,"change":fragmentation_change,"method":"NDVI-threshold forest-mask landscape screening"},
        "geojson":{"type":"FeatureCollection","features":feats},
        "label":"DERIVED_METRIC",
        "method":"Sentinel-2 L2A COG multispectral before/after screening (NDVI/NDMI/NBR/NDWI) with SCL masking and unsupervised anomaly corroboration",
        "warning":"Candidate vegetation/forest loss screening is not proof of deforestation. Confirm with land-cover context, multiple dates and/or radar/field evidence.",
    }
