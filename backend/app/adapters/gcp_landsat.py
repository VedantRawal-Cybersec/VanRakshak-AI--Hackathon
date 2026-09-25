from __future__ import annotations
import asyncio
import math
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from app.adapters.base import BaseAdapter, AdapterError


_ITEM_RE=re.compile(r"^(L[A-Z][0-9]{2})_L2[A-Z0-9]{2}_(\d{3})(\d{3})_(\d{8})_")
_PRODUCT_RE=re.compile(r"^(L[A-Z][0-9]{2})_L1(?:TP|GT|GS)_(\d{3})(\d{3})_(\d{8})_\d{8}_01_(?:T1|T2|RT)$")


class GCPLandsatAdapter(BaseAdapter):
    """Anonymous HTTPS access to Google's public Landsat Collection-1 mirror.

    Modern metadata can be selected by USGS STAC and resolved into this mirror.
    For sparse 1980s catalogue gaps, this adapter can also discover the nearest
    real Collection-1 product directly from the public bucket using the WRS-2
    orbit geometry and then verify point coverage from its MTL corner metadata.
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

    @staticmethod
    def _product_parts(product_id: str):
        match=_PRODUCT_RE.match(product_id)
        if not match:
            raise AdapterError("Invalid public Landsat product id")
        return match.groups()

    @staticmethod
    def _metadata_number(text: str, key: str) -> float | None:
        match=re.search(rf"^\s*{re.escape(key)}\s*=\s*([-+0-9.Ee]+)",text,re.MULTILINE)
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None

    @classmethod
    def _metadata_summary(cls,text: str) -> dict:
        cloud=cls._metadata_number(text,"CLOUD_COVER")
        if cloud is None:
            cloud=cls._metadata_number(text,"CLOUD_COVER_LAND")
        lats=[cls._metadata_number(text,f"CORNER_{c}_LAT_PRODUCT") for c in ("UL","UR","LL","LR")]
        lons=[cls._metadata_number(text,f"CORNER_{c}_LON_PRODUCT") for c in ("UL","UR","LL","LR")]
        bbox=None
        if all(v is not None for v in lats+lons):
            bbox=[min(lons),min(lats),max(lons),max(lats)]
        return {"cloud_cover":cloud,"bbox":bbox}

    @staticmethod
    def _contains(bbox,lat: float,lon: float) -> bool:
        if not bbox:
            return True
        west,south,east,north=bbox
        return south-0.05 <= lat <= north+0.05 and west-0.05 <= lon <= east+0.05

    @staticmethod
    def _wrap_path(path: int) -> int:
        return ((int(path)-1)%233)+1

    @classmethod
    def wrs2_candidates(cls,lat: float,lon: float) -> list[tuple[int,int]]:
        """Return a compact WRS-2 neighbourhood for a latitude/longitude.

        Landsat 4+ flies a ~98.2 degree sun-synchronous orbit. This spherical
        orbit estimate resolves the nominal descending path/row and we search
        its immediate overlap neighbours. MTL corner coordinates are the final
        spatial authority, so the approximation never decides coverage alone.
        """
        if not -82.6 <= float(lat) <= 82.6:
            return []
        inclination=math.radians(98.2)
        phi=math.radians(float(lat))
        ratio=max(-1.0,min(1.0,math.sin(phi)/math.sin(inclination)))
        travel=math.asin(ratio)
        u=math.pi-travel
        inertial=math.degrees(
            math.atan2(math.cos(inclination)*math.sin(u),math.cos(u))-math.pi
        )
        inertial=((inertial+180.0)%360.0)-180.0
        # Approximate Earth rotation during travel from descending equator node.
        dt_minutes=-travel/(2.0*math.pi)*98.9
        rotation=dt_minutes*360.0/(23.9344696*60.0)
        point_from_node=inertial-rotation
        node_lon=((float(lon)-point_from_node+180.0)%360.0)-180.0
        path_float=((-64.60-node_lon)%360.0)/(360.0/233.0)+1.0
        path=cls._wrap_path(round(path_float))
        row_float=60.0-math.degrees(travel)*248.0/360.0
        row=max(1,min(122,round(row_float)))

        offsets=((0,0),(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1))
        out=[]
        for pd,rd in offsets:
            candidate=(cls._wrap_path(path+pd),row+rd)
            if 1 <= candidate[1] <= 122 and candidate not in out:
                out.append(candidate)
        return out

    @staticmethod
    def _missions_for(target: datetime) -> tuple[str,...]:
        year=target.year
        if year < 1984:
            return ("LT04",)
        if year < 1999:
            return ("LT05","LT04")
        if year < 2013:
            return ("LE07","LT05")
        return ("LC08","LE07")

    async def _list_products_for_year(self,mission: str,path: int,row: int,year: int,level: str="L1TP") -> list[str]:
        prefix=f"{mission}/01/{path:03d}/{row:03d}/{mission}_{level}_{path:03d}{row:03d}_{year:04d}"
        data=await self.get_json(self.list_url,params={"prefix":prefix,"maxResults":1000})
        products=set()
        for obj in data.get("items") or []:
            name=str(obj.get("name") or "")
            parts=name.split("/")
            if len(parts)>=6 and _PRODUCT_RE.match(parts[4]):
                products.add(parts[4])
        return sorted(products)

    async def _discover_products(
        self,
        lat: float,
        lon: float,
        target: datetime,
        max_window_days: int,
        *,
        broad: bool=False,
    ) -> list[tuple[float,str]]:
        compact_paths=self.wrs2_candidates(lat,lon)
        if not compact_paths:
            return []

        # The fast pass uses the immediate overlap neighbourhood. If those
        # products exist but their MTL footprint rejects the requested point,
        # the broad pass must genuinely expand beyond the same 3x3 cells.
        # Expand only the WRS neighbourhood (not the date window) and keep MTL
        # corner metadata as the final spatial authority.
        paths=list(compact_paths)
        if broad:
            seed_path,seed_row=compact_paths[0]
            for path_delta in (-2,-1,0,1,2):
                for row_delta in (-2,-1,0,1,2):
                    candidate=(self._wrap_path(seed_path+path_delta),seed_row+row_delta)
                    if 1 <= candidate[1] <= 122 and candidate not in paths:
                        paths.append(candidate)

        start_year=(target-timedelta(days=max_window_days)).year
        end_year=(target+timedelta(days=max_window_days)).year
        years=sorted(range(start_year,end_year+1),key=lambda y:abs(y-target.year))
        missions=self._missions_for(target)
        semaphore=asyncio.Semaphore(6)

        async def fetch(mission,path,row,year,level):
            async with semaphore:
                try:
                    return await self._list_products_for_year(mission,path,row,year,level)
                except AdapterError:
                    return []

        def normalize(batches):
            rows=[]; seen=set()
            for batch in batches:
                for product in batch:
                    if product in seen:
                        continue
                    seen.add(product)
                    try:
                        _,_,_,acquired=self._product_parts(product)
                        observed=datetime.strptime(acquired,"%Y%m%d").replace(tzinfo=timezone.utc)
                    except Exception:
                        continue
                    delta=abs((observed-target).total_seconds())/86400.0
                    if delta <= max_window_days+1:
                        rows.append((delta,product))
            return sorted(rows,key=lambda row:(row[0],0 if row[1].endswith("_T1") else 1,row[1]))

        # Phase 1 is deliberately compact but complete for the primary mission:
        # all WRS overlap cells and every calendar year touched by the requested
        # date window. Finding a nearby product is not sufficient by itself;
        # closest_scene verifies point coverage before it can be accepted.
        primary=missions[:1]
        batches=await asyncio.gather(*(
            fetch(mission,path,row,year,"L1TP")
            for mission in primary
            for path,row in paths
            for year in years
        ))
        products=normalize(batches)
        if products and not broad:
            return products

        if broad:
            # Phase 2 runs only after phase-1 products were spatially rejected.
            # Include alternate Landsat missions and lower processing tiers so a
            # non-covering neighbouring frame cannot prematurely terminate the
            # historical search.
            batches=await asyncio.gather(*(
                fetch(mission,path,row,year,level)
                for mission in missions
                for path,row in paths
                for year in years
                for level in ("L1TP","L1GT","L1GS")
            ))
            return normalize(batches)

        return products

    async def closest_scene(
        self,
        lat: float,
        lon: float,
        target_date: datetime,
        window_days: int=35,
        cloud_lt: float=60,
        max_window_days: int=550,
    ) -> dict | None:
        target=target_date.astimezone(timezone.utc)
        seen=set()

        async def verify(products):
            # Metadata is the authority for both point coverage and scene cloud.
            # Keep the bounded shortlist so this never downloads raster imagery
            # merely to decide whether a scene is eligible.
            for delta,product in products[:80]:
                if product in seen:
                    continue
                seen.add(product)
                try:
                    metadata_text=await self.metadata(product)
                except AdapterError:
                    continue
                meta=self._metadata_summary(metadata_text)
                cloud=meta.get("cloud_cover")
                if cloud is not None and cloud>float(cloud_lt):
                    continue
                if not self._contains(meta.get("bbox"),lat,lon):
                    continue
                mission,path,row,acquired=self._product_parts(product)
                observed=datetime.strptime(acquired,"%Y%m%d").replace(tzinfo=timezone.utc)
                return {
                    "type":"Feature",
                    "id":product,
                    "collection":"gcp-public-data-landsat-c1",
                    "bbox":meta.get("bbox"),
                    "properties":{
                        "datetime":observed.isoformat().replace("+00:00","Z"),
                        "eo:cloud_cover":cloud,
                        "platform":mission,
                    },
                    "_gcp_product_id":product,
                    "_vanrakshak_catalog_source":"Google Cloud public Landsat Collection 1",
                    "_vanrakshak_archive":{
                        "requested_date":target.date().isoformat(),
                        "window_used_days":max(int(window_days),int(math.ceil(delta))),
                        "date_offset_days":round(delta,1),
                        "cloud_filter":float(cloud_lt),
                    },
                }
            return None

        fast=await self._discover_products(lat,lon,target,max_window_days,broad=False)
        item=await verify(fast)
        if item:
            return item

        broad=await self._discover_products(lat,lon,target,max_window_days,broad=True)
        return await verify(broad)

    async def resolve_item(self,item: dict) -> str | None:
        direct=item.get("_gcp_product_id")
        if direct:
            self._product_parts(str(direct))
            return str(direct)
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
        catalog=item.get("_vanrakshak_catalog_source") or "USGS Landsat STAC"
        source=(
            "Google Cloud public Landsat Collection 1 archive"
            if str(catalog).startswith("Google Cloud")
            else "USGS Landsat archive / Google public Landsat mirror"
        )
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
            "source":source,
            "catalog_source":catalog,
            "render_source":"Google Cloud public Landsat Collection 1",
            "resolution_m":30,
            # Lower source max zoom prevents the browser from triggering dozens
            # of duplicate remote COG reads while still allowing map overzoom.
            "maxzoom":10,
            "label":"HISTORICAL",
        }
