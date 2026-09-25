from __future__ import annotations
import re
from urllib.parse import quote
from app.adapters.base import BaseAdapter, AdapterError


_ITEM_RE=re.compile(r"^(L[A-Z][0-9]{2})_L2[A-Z0-9]{2}_(\d{3})(\d{3})_(\d{8})_")
_PRODUCT_RE=re.compile(r"^(L[A-Z][0-9]{2})_L1(?:TP|GT|GS)_(\d{3})(\d{3})_(\d{8})_\d{8}_01_(?:T1|T2|RT)$")


class GCPLandsatAdapter(BaseAdapter):
    """Anonymous HTTPS access to Google's public Landsat Collection-1 mirror.

    USGS STAC selects the real historical acquisition. This mirror supplies
    matching Level-1 bands without requester-pays credentials.
    """

    name="gcp_public_landsat"
    source_url="https://storage.googleapis.com/gcp-public-data-landsat"
    list_url="https://storage.googleapis.com/storage/v1/b/gcp-public-data-landsat/o"

    @staticmethod
    def _scene_parts(item: dict):
        item_id=str(item.get("id") or "")
        match=_ITEM_RE.match(item_id)
        if not match:
            raise AdapterError(f"Unsupported Landsat archive item id: {item_id}")
        return match.groups()

    async def resolve_item(self,item: dict) -> str | None:
        sensor,path,row,acquired=self._scene_parts(item)
        root=f"{sensor}/01/{path}/{row}/"
        candidates=[]
        for level in ("L1TP","L1GT","L1GS"):
            prefix=f"{root}{sensor}_{level}_{path}{row}_{acquired}"
            try:
                data=await self.get_json(self.list_url,params={"prefix":prefix,"maxResults":100})
            except Exception:
                continue
            for obj in data.get("items") or []:
                name=str(obj.get("name") or "")
                parts=name.split("/")
                if len(parts)>=6:
                    product=parts[4]
                    if _PRODUCT_RE.match(product):
                        candidates.append(product)
            if candidates:
                break
        if not candidates:
            return None
        return sorted(set(candidates),key=lambda p:(0 if p.endswith("_T1") else 1 if p.endswith("_T2") else 2,p))[0]

    @staticmethod
    def _product_parts(product_id: str):
        match=_PRODUCT_RE.match(product_id)
        if not match:
            raise AdapterError("Invalid public Landsat product id")
        return match.groups()

    def product_root(self,product_id: str) -> str:
        sensor,path,row,_=self._product_parts(product_id)
        return f"{self.source_url}/{sensor}/01/{path}/{row}/{product_id}"

    def asset_urls(self,product_id: str) -> dict[str,str]:
        sensor,_,_,_=self._product_parts(product_id)
        if sensor in {"LC08","LO08","LC09","LO09"}:
            bands={"blue":2,"green":3,"red":4,"nir":5,"swir16":6,"swir22":7}
        else:
            bands={"blue":1,"green":2,"red":3,"nir":4,"swir16":5,"swir22":7}
        root=self.product_root(product_id)
        return {name:f"{root}/{product_id}_B{band}.TIF" for name,band in bands.items()}

    def metadata_url(self,product_id: str) -> str:
        root=self.product_root(product_id)
        return f"{root}/{product_id}_MTL.txt"

    async def metadata(self,product_id: str) -> str:
        return await self.get_text(self.metadata_url(product_id))

    def tile_spec(self,item: dict,product_id: str,mode: str,requested_date: str | None=None):
        if mode not in {"true_color","false_color","ndvi","ndmi","nbr","ndwi"}:
            raise AdapterError(f"Unsupported historical Landsat render mode: {mode}")
        props=item.get("properties") or {}
        archive=item.get("_vanrakshak_archive") or {}
        return {
            "mode":mode,
            "item_id":item.get("id"),
            "render_product_id":product_id,
            "observed_at":props.get("datetime"),
            "requested_date":requested_date or archive.get("requested_date"),
            "date_offset_days":archive.get("date_offset_days"),
            "window_used_days":archive.get("window_used_days"),
            "cloud_cover":props.get("eo:cloud_cover"),
            "bbox":item.get("bbox"),
            "tile_url":f"/api/historical/landsat-tile/{quote(product_id,safe='')}/{mode}/{{z}}/{{x}}/{{y}}.png",
            "source":"USGS Landsat archive / Google public Landsat mirror",
            "catalog_source":"USGS Landsat STAC",
            "render_source":"Google Cloud public Landsat Collection 1",
            "resolution_m":30,
            "maxzoom":12,
            "label":"HISTORICAL",
        }
