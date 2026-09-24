from __future__ import annotations
from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings

class ProtectedPlanetAdapter(BaseAdapter):
    name = "protected_planet"
    source_url = "https://www.protectedplanet.net/"

    def _token(self):
        if not settings.protected_planet_token:
            raise AdapterError("PROTECTED_PLANET_TOKEN is not configured")
        return settings.protected_planet_token

    async def search(self, country: str = "IND", page: int = 1, per_page: int = 50, with_geometry: bool = True, **filters):
        url=f"{settings.protected_planet_url.rstrip('/')}/protected_areas/search"
        params={
            "country":country.upper(),
            "with_geometry":str(bool(with_geometry)).lower(),
            "page":max(1,page),
            "per_page":min(max(1,per_page),50),
            "token":self._token(),
        }
        for key in ("marine","is_green_list","designation","jurisdiction","governance","iucn_category"):
            if filters.get(key) is not None:
                params[key]=str(filters[key]).lower() if isinstance(filters[key],bool) else filters[key]
        return await self.get_json(url,params=params)

    async def india(self, page: int = 1, per_page: int = 50):
        return await self.search("IND",page,per_page,True,marine=False)

    async def site(self, site_id: str | int, with_geometry: bool = True):
        url=f"{settings.protected_planet_url.rstrip('/')}/protected_areas/{site_id}"
        return await self.get_json(url,params={"with_geometry":str(bool(with_geometry)).lower(),"token":self._token()})

    async def parcels(self, site_id: str | int, with_geometry: bool = True):
        url=f"{settings.protected_planet_url.rstrip('/')}/protected_area_parcels/{site_id}"
        return await self.get_json(url,params={"with_geometry":str(bool(with_geometry)).lower(),"token":self._token()})

    async def country(self, iso3: str = "IND", with_geometry: bool = False):
        url=f"{settings.protected_planet_url.rstrip('/')}/countries/{iso3.upper()}"
        return await self.get_json(url,params={"with_geometry":str(bool(with_geometry)).lower(),"token":self._token()})
