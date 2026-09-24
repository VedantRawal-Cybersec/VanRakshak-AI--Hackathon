from __future__ import annotations
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import httpx
from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings

class EarthSearchAdapter(BaseAdapter):
    """Public Element 84 Earth Search STAC adapter.

    Earth Search exposes Sentinel-2 L2A and Landsat COG assets without requiring
    VanRakshak to fabricate imagery URLs. It is used for the visual map/time
    machine path; Copernicus remains the authoritative Sentinel catalogue path.
    """
    name = "earth_search"
    source_url = "https://earth-search.aws.element84.com/v1"

    async def search(
        self,
        lat: float,
        lon: float,
        start: datetime,
        end: datetime,
        collection: str = "sentinel-2-l2a",
        cloud_lt: float = 50,
        limit: int = 20,
    ):
        body = {
            "collections": [collection],
            "datetime": f"{start.astimezone(timezone.utc).isoformat()}/{end.astimezone(timezone.utc).isoformat()}",
            "intersects": {"type": "Point", "coordinates": [lon, lat]},
            "limit": max(1, min(limit, 100)),
        }
        if collection.startswith("sentinel") or collection.startswith("landsat"):
            body["query"] = {"eo:cloud_cover": {"lt": cloud_lt}}
        return await self.post_json(f"{settings.earth_search_url}/search", json=body)

    async def latest_sentinel2(self, lat: float, lon: float, days: int = 45, cloud_lt: float = 50):
        end = datetime.now(timezone.utc)
        return await self.search(lat, lon, end - timedelta(days=days), end, "sentinel-2-l2a", cloud_lt, 15)

    async def latest_landsat(self, lat: float, lon: float, days: int = 90, cloud_lt: float = 60):
        end = datetime.now(timezone.utc)
        return await self.search(lat, lon, end - timedelta(days=days), end, "landsat-c2-l2", cloud_lt, 15)

    async def search_sentinel1(self, lat: float, lon: float, start: datetime, end: datetime, limit: int = 60):
        body = {
            "collections": ["sentinel-1-grd"],
            "datetime": f"{start.astimezone(timezone.utc).isoformat()}/{end.astimezone(timezone.utc).isoformat()}",
            "intersects": {"type": "Point", "coordinates": [lon, lat]},
            "limit": max(1, min(limit, 100)),
        }
        return await self.post_json(f"{settings.earth_search_url}/search", json=body)

    async def latest_sentinel1(self, lat: float, lon: float, days: int = 45, limit: int = 20):
        end = datetime.now(timezone.utc)
        return await self.search_sentinel1(lat, lon, end - timedelta(days=days), end, limit)

    @staticmethod
    def _dt(item: dict):
        raw=(item.get("properties") or {}).get("datetime")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z","+00:00"))
        except Exception:
            return None

    @staticmethod
    def _s1_key(item: dict):
        p=item.get("properties") or {}
        return (
            str(p.get("sat:orbit_state") or ""),
            str(p.get("sat:relative_orbit") or p.get("sat:relative_orbit_number") or ""),
            tuple(sorted(str(x).lower() for x in (p.get("sar:polarizations") or []))),
        )

    async def closest_sentinel1_pair(self, lat: float, lon: float, before_date: datetime, after_date: datetime, window_days: int = 24):
        before_data=await self.search_sentinel1(lat,lon,before_date-timedelta(days=window_days),before_date+timedelta(days=window_days),80)
        after_data=await self.search_sentinel1(lat,lon,after_date-timedelta(days=window_days),after_date+timedelta(days=window_days),80)
        before_items=[x for x in before_data.get("features",[]) if "vv" in (x.get("assets") or {})]
        after_items=[x for x in after_data.get("features",[]) if "vv" in (x.get("assets") or {})]
        best=None; best_score=None
        for b in before_items:
            bd=self._dt(b)
            if not bd: continue
            bk=self._s1_key(b)
            for a in after_items:
                ad=self._dt(a)
                if not ad: continue
                ak=self._s1_key(a)
                # Require same orbit direction and, when available, same relative orbit.
                if bk[0] and ak[0] and bk[0] != ak[0]: continue
                if bk[1] and ak[1] and bk[1] != ak[1]: continue
                common=set((b.get("assets") or {})).intersection((a.get("assets") or {}))
                if "vv" not in common: continue
                score=abs((bd-before_date).total_seconds())+abs((ad-after_date).total_seconds())
                if best_score is None or score < best_score:
                    best=(b,a); best_score=score
        return best

    async def closest_scene(self, lat: float, lon: float, target_date: datetime, window_days: int = 30, cloud_lt: float = 60):
        data = await self.search(
            lat, lon,
            target_date - timedelta(days=window_days),
            target_date + timedelta(days=window_days),
            "sentinel-2-l2a", cloud_lt, 30,
        )
        features = data.get("features", [])
        if not features:
            return None
        def distance(item):
            raw = (item.get("properties") or {}).get("datetime")
            if not raw:
                return 10**18
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                return abs((dt - target_date).total_seconds())
            except Exception:
                return 10**18
        return min(features, key=distance)

    @staticmethod
    def item_self_url(item: dict) -> str | None:
        for link in item.get("links", []):
            if link.get("rel") == "self" and link.get("href"):
                return link["href"]
        return None

    def tile_spec(self, item: dict, mode: str = "true_color"):
        item_url = self.item_self_url(item)
        if not item_url:
            raise AdapterError("STAC item does not expose a self URL")
        base = settings.titiler_public_url.rstrip("/") + "/stac/tiles/WebMercatorQuad/{z}/{x}/{y}.png"
        common: list[tuple[str, str]] = [("url", item_url), ("asset_as_band", "true"), ("resampling", "bilinear")]
        mode = mode.lower()
        if mode == "true_color":
            params = [("url", item_url), ("assets", "visual"), ("resampling", "bilinear")]
        elif mode == "ndvi":
            params = common + [("assets", "red"), ("assets", "nir"), ("expression", "(nir-red)/(nir+red)"), ("rescale", "-1,1"), ("colormap_name", "rdylgn")]
        elif mode == "ndmi":
            params = common + [("assets", "nir"), ("assets", "swir16"), ("expression", "(nir-swir16)/(nir+swir16)"), ("rescale", "-1,1"), ("colormap_name", "blues")]
        elif mode == "nbr":
            params = common + [("assets", "nir"), ("assets", "swir22"), ("expression", "(nir-swir22)/(nir+swir22)"), ("rescale", "-1,1"), ("colormap_name", "rdylgn")]
        elif mode == "ndwi":
            params = common + [("assets", "green"), ("assets", "nir"), ("expression", "(green-nir)/(green+nir)"), ("rescale", "-1,1"), ("colormap_name", "blues")]
        elif mode == "false_color":
            params = [("url", item_url), ("assets", "nir"), ("assets", "red"), ("assets", "green"), ("asset_as_band", "true"), ("rescale", "0,5000"), ("resampling", "bilinear")]
        else:
            raise AdapterError(f"Unsupported satellite render mode: {mode}")
        return {
            "mode": mode,
            "item_id": item.get("id"),
            "observed_at": (item.get("properties") or {}).get("datetime"),
            "cloud_cover": (item.get("properties") or {}).get("eo:cloud_cover"),
            "bbox": item.get("bbox"),
            "item_url": item_url,
            "tile_url": base + "?" + urlencode(params, doseq=True, safe="{}(),/"),
            "source": "Element 84 Earth Search / Sentinel-2 L2A",
            "resolution_m": 10 if mode in {"true_color", "ndvi", "ndwi", "false_color"} else 20,
        }
