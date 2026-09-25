from __future__ import annotations
import asyncio
from io import BytesIO

import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.warp import transform

from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings


class SoilGridsAdapter(BaseAdapter):
    name = "soilgrids"
    # ISRIC currently recommends WCS/WMS as the stable access path; the REST API is beta and may be paused.
    source_url = "https://maps.isric.org/"

    _PROPERTY_META = {
        "phh2o": {"mapped_units":"pH x 10","target_units":"pH","d_factor":10.0},
        "soc": {"mapped_units":"dg/kg","target_units":"g/kg","d_factor":10.0},
        "nitrogen": {"mapped_units":"cg/kg","target_units":"g/kg","d_factor":100.0},
        "clay": {"mapped_units":"g/kg","target_units":"%","d_factor":10.0},
        "sand": {"mapped_units":"g/kg","target_units":"%","d_factor":10.0},
        "silt": {"mapped_units":"g/kg","target_units":"%","d_factor":10.0},
        "bdod": {"mapped_units":"cg/cm3","target_units":"kg/dm3","d_factor":100.0},
        "cec": {"mapped_units":"mmol(c)/kg","target_units":"cmol(c)/kg","d_factor":10.0},
    }

    async def _wcs_property(self, prop: str, lat: float, lon: float):
        # SoilGrids native grid uses Interrupted Goode Homolosine. PROJ's "igh"
        # gives us the native map coordinates required by ISRIC WCS.
        try:
            xs,ys=transform("EPSG:4326","+proj=igh +datum=WGS84 +units=m +no_defs",[lon],[lat])
            x,y=float(xs[0]),float(ys[0])
        except Exception as exc:
            raise AdapterError(f"SoilGrids coordinate transform failed for {prop}") from exc

        # Request a small footprint around the point; SoilGrids is 250 m, so
        # a 500 m box reliably captures one or more valid cells.
        pad=250.0
        url=f"https://maps.isric.org/mapserv?map=/map/{prop}.map"
        params=[
            ("SERVICE","WCS"),("VERSION","2.0.1"),("REQUEST","GetCoverage"),
            ("COVERAGEID",f"{prop}_0-5cm_mean"),("FORMAT","GEOTIFF_INT16"),
            ("SUBSET",f"X({x-pad},{x+pad})"),("SUBSET",f"Y({y-pad},{y+pad})"),
        ]
        content,_=await self.get_bytes(url,params=params)
        try:
            with MemoryFile(content) as mem:
                with mem.open() as src:
                    a=src.read(1,masked=True)
                    vals=np.asarray(a.compressed(),dtype="float64")
                    if vals.size==0:
                        raise AdapterError(f"SoilGrids WCS returned no valid {prop} cells")
                    # Median of the small neighbourhood is more robust than an edge pixel.
                    value=float(np.median(vals))
        except AdapterError:
            raise
        except Exception as exc:
            raise AdapterError(f"SoilGrids WCS returned unreadable {prop} raster") from exc

        meta=self._PROPERTY_META[prop]
        return {
            "name":prop,
            "unit_measure":meta,
            "depths":[{
                "label":"0-5cm",
                "range":{"top_depth":0,"bottom_depth":5,"unit_depth":"cm"},
                "values":{"mean":value},
            }],
        }

    async def _wcs_point(self, lat: float, lon: float):
        props=list(self._PROPERTY_META)
        sem=asyncio.Semaphore(3)
        async def one(prop):
            async with sem:
                try:
                    return prop,await self._wcs_property(prop,lat,lon),None
                except Exception as exc:
                    return prop,None,str(exc)
        results=await asyncio.gather(*(one(p) for p in props))
        layers=[layer for _,layer,_ in results if layer is not None]
        errors={prop:error for prop,_,error in results if error}
        if not layers:
            raise AdapterError("SoilGrids WCS is temporarily unavailable")
        return {
            "type":"Point",
            "coordinates":[lon,lat],
            "properties":{"layers":layers},
            "provider":"ISRIC SoilGrids WCS",
            "access_method":"WCS 2.0.1 / official SoilGrids map service",
            "partial":bool(errors),
            "property_errors":errors,
        }

    async def point(self, lat: float, lon: float):
        # Prefer the official WCS path because ISRIC currently documents the
        # SoilGrids REST API as unstable/temporarily paused.
        try:
            return await self._wcs_point(lat,lon)
        except Exception as wcs_exc:
            # Keep REST as a secondary recovery path for when ISRIC restores it.
            properties=list(self._PROPERTY_META)
            params=[("lon",lon),("lat",lat)]
            params += [("property",p) for p in properties]
            params += [("depth","0-5cm"),("value","mean")]
            try:
                data=await self.get_json(settings.soilgrids_url,params=params)
                if isinstance(data,dict):
                    data["provider"]="ISRIC SoilGrids REST"
                    data["access_method"]="REST v2.0 fallback"
                return data
            except Exception as rest_exc:
                raise AdapterError(
                    f"SoilGrids unavailable through both official WCS and REST fallback: WCS={wcs_exc}; REST={rest_exc}"
                ) from rest_exc
