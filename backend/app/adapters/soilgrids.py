from __future__ import annotations
from app.adapters.base import BaseAdapter
from app.config import settings

class SoilGridsAdapter(BaseAdapter):
    name = "soilgrids"
    source_url = "https://soilgrids.org/"

    async def point(self, lat: float, lon: float):
        properties = ["phh2o","soc","nitrogen","clay","sand","silt","bdod","cec"]
        params = [("lon", lon), ("lat", lat)]
        params += [("property", p) for p in properties]
        params += [("depth", "0-5cm"), ("value", "mean")]
        return await self.get_json(settings.soilgrids_url, params=params)
