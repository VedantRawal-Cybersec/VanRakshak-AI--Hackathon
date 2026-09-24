from __future__ import annotations
import csv, io
from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings

class FIRMSAdapter(BaseAdapter):
    name = "nasa_firms"
    source_url = "https://firms.modaps.eosdis.nasa.gov/"

    async def fires(self, lat: float, lon: float, radius_deg: float = 0.5, days: int = 1):
        if not settings.firms_map_key:
            raise AdapterError("FIRMS_MAP_KEY is not configured")
        west, south, east, north = lon-radius_deg, lat-radius_deg, lon+radius_deg, lat+radius_deg
        area = f"{west},{south},{east},{north}"
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{settings.firms_map_key}/VIIRS_NOAA21_NRT/{area}/{max(1,min(days,5))}"
        text = await self.get_text(url)
        rows = list(csv.DictReader(io.StringIO(text)))
        return rows
