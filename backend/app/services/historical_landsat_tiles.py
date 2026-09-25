from __future__ import annotations
from io import BytesIO
import re
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from PIL import Image


class HistoricalTileError(RuntimeError):
    pass


def parse_mtl(text: str) -> dict[str,str]:
    out={}
    for raw in text.splitlines():
        line=raw.strip()
        if "=" not in line:
            continue
        key,value=line.split("=",1)
        key=key.strip(); value=value.strip().strip('"')
        if key:
            out[key]=value
    return out


def _tile_bounds(z: int,x: int,y: int):
    if z<0 or z>14:
        raise HistoricalTileError("Historical Landsat zoom must be between 0 and 14")
    n=2**z
    if x<0 or y<0 or x>=n or y>=n:
        raise HistoricalTileError("Historical Landsat tile coordinate is outside this zoom")
    origin=20037508.342789244
    span=2*origin/n
    minx=-origin+x*span; maxx=minx+span
    maxy=origin-y*span; miny=maxy-span
    return minx,miny,maxx,maxy


def _band_number(url: str) -> int | None:
    match=re.search(r"_B(\d+)\.TIF(?:$|\?)",url,re.I)
    return int(match.group(1)) if match else None


def _read(url: str,z: int,x: int,y: int,size: int=256):
    bounds=_tile_bounds(z,x,y)
    transform=from_bounds(*bounds,size,size)
    env={
        "GDAL_DISABLE_READDIR_ON_OPEN":"EMPTY_DIR",
        "CPL_VSIL_CURL_USE_HEAD":"NO",
        "GDAL_HTTP_MULTIRANGE":"YES",
        "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES":"YES",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS":".TIF,.tif",
        "VSI_CACHE":"TRUE",
        "VSI_CACHE_SIZE":"5000000",
    }
    try:
        with rasterio.Env(**env):
            with rasterio.open(url) as src:
                with WarpedVRT(
                    src,crs="EPSG:3857",transform=transform,width=size,height=size,
                    resampling=Resampling.bilinear,nodata=0,
                ) as vrt:
                    arr=vrt.read(1).astype("float32")
                    valid=np.isfinite(arr)&(arr>0)
                    return arr,valid
    except Exception as exc:
        raise HistoricalTileError(f"Could not read public Landsat band: {exc}") from exc


def _reflectance(arr: np.ndarray,url: str,meta: dict[str,str]):
    band=_band_number(url)
    if band is None:
        raise HistoricalTileError("Could not determine Landsat band number")
    try:
        mult=float(meta[f"REFLECTANCE_MULT_BAND_{band}"])
        add=float(meta[f"REFLECTANCE_ADD_BAND_{band}"])
        return arr*mult+add
    except Exception as exc:
        raise HistoricalTileError(f"Landsat reflectance coefficients are unavailable for band {band}") from exc


def _rgb8(channels: list[np.ndarray],valid: np.ndarray):
    out=[]
    for values in channels:
        scaled=np.clip((values-0.015)/0.34,0,1)
        scaled=np.power(scaled,0.72)
        out.append(np.round(scaled*255).astype("uint8"))
    rgb=np.stack(out,axis=-1)
    alpha=np.where(valid,255,0).astype("uint8")[...,None]
    return np.concatenate([rgb,alpha],axis=-1)


def _palette(index: np.ndarray,valid: np.ndarray,mode: str):
    values=np.clip(index,-1,1)
    if mode in {"ndmi","ndwi"}:
        stops=[(-1,(151,110,73)),(0,(238,238,220)),(1,(25,93,171))]
    elif mode=="nbr":
        stops=[(-1,(165,0,38)),(0,(255,255,191)),(1,(0,104,55))]
    else:
        stops=[(-1,(120,64,35)),(0,(245,224,120)),(1,(20,125,55))]
    lo,mid,hi=stops
    left=values<=mid[0]
    t=np.clip((values-lo[0])/(mid[0]-lo[0]),0,1)[...,None]
    rgb_left=np.array(lo[1],dtype="float32")*(1-t)+np.array(mid[1],dtype="float32")*t
    t2=np.clip((values-mid[0])/(hi[0]-mid[0]),0,1)[...,None]
    rgb_right=np.array(mid[1],dtype="float32")*(1-t2)+np.array(hi[1],dtype="float32")*t2
    rgb=np.where(left[...,None],rgb_left,rgb_right)
    alpha=np.where(valid,255,0).astype("uint8")[...,None]
    return np.concatenate([np.clip(rgb,0,255).astype("uint8"),alpha],axis=-1)


def render_png(asset_urls: dict[str,str],metadata_text: str,mode: str,z: int,x: int,y: int) -> bytes:
    meta=parse_mtl(metadata_text)
    names={
        "true_color":["red","green","blue"],
        "false_color":["nir","red","green"],
        "ndvi":["nir","red"],
        "ndmi":["nir","swir16"],
        "nbr":["nir","swir22"],
        "ndwi":["green","nir"],
    }.get(mode)
    if not names:
        raise HistoricalTileError(f"Unsupported historical render mode: {mode}")
    arrays=[]; masks=[]
    for name in names:
        url=asset_urls.get(name)
        if not url:
            raise HistoricalTileError(f"Historical Landsat asset missing: {name}")
        arr,mask=_read(url,z,x,y)
        arrays.append(_reflectance(arr,url,meta)); masks.append(mask)
    valid=np.logical_and.reduce(masks)
    if mode in {"true_color","false_color"}:
        rgba=_rgb8(arrays,valid)
    else:
        first,second=arrays
        denominator=first+second
        index=np.divide(first-second,denominator,out=np.zeros_like(first),where=np.abs(denominator)>1e-6)
        valid=valid&np.isfinite(index)&(np.abs(denominator)>1e-6)
        rgba=_palette(index,valid,mode)
    buf=BytesIO()
    Image.fromarray(rgba,"RGBA").save(buf,format="PNG",optimize=True)
    return buf.getvalue()
