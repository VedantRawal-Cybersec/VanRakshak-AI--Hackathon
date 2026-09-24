from __future__ import annotations
from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings

class ProtectedPlanetAdapter(BaseAdapter):
    name = "protected_planet"
    source_url = "https://www.protectedplanet.net/"

    async def india(self, page: int = 1, per_page: int = 50):
        if not settings.protected_planet_token:
            raise AdapterError("PROTECTED_PLANET_TOKEN is not configured")
        url = f"{settings.protected_planet_url}/protected_areas/search"
        params = {
            "country": "IND", "marine": "false", "with_geometry": "true",
            "page": page, "per_page": min(per_page, 50), "token": settings.protected_planet_token,
        }
        return await self.get_json(url, params=params)
