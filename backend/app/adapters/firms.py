from __future__ import annotations
import csv, io
from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings

class FIRMSAdapter(BaseAdapter):
    name = "nasa_firms"
    source_url = "https://firms.modaps.eosdis.nasa.gov/"
    preferred_sources = ("VIIRS_NOAA21_NRT","VIIRS_NOAA20_NRT","MODIS_NRT")

    async def _area(self, source: str, lat: float, lon: float, radius_deg: float, days: int):
        if not settings.firms_map_key:
            raise AdapterError("FIRMS_MAP_KEY is not configured")
        west, south, east, north = lon-radius_deg, lat-radius_deg, lon+radius_deg, lat+radius_deg
        area = f"{west},{south},{east},{north}"
        url = (
            "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
            f"{settings.firms_map_key}/{source}/{area}/{max(1,min(days,5))}"
        )
        text = await self.get_text(url)
        rows=list(csv.DictReader(io.StringIO(text)))
        for row in rows:
            row["_firms_source"]=source
        return rows

    async def fires(self, lat: float, lon: float, radius_deg: float = 0.5, days: int = 1, sources: tuple[str,...] | None = None):
        if not settings.firms_map_key:
            raise AdapterError("FIRMS_MAP_KEY is not configured")
        rows=[]; errors=[]
        for source in (sources or self.preferred_sources):
            try:
                rows.extend(await self._area(source,lat,lon,radius_deg,days))
            except Exception as exc:
                errors.append(f"{source}: {exc}")
        if not rows and errors:
            raise AdapterError("; ".join(errors))
        seen=set(); dedup=[]
        for row in rows:
            key=(row.get("latitude"),row.get("longitude"),row.get("acq_date"),row.get("acq_time"),row.get("satellite"))
            if key in seen:
                continue
            seen.add(key); dedup.append(row)
        return dedup

    async def availability(self, sensor: str = "ALL"):
        if not settings.firms_map_key:
            raise AdapterError("FIRMS_MAP_KEY is not configured")
        url=f"https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/{settings.firms_map_key}/{sensor}"
        text=await self.get_text(url)
        return list(csv.DictReader(io.StringIO(text)))
