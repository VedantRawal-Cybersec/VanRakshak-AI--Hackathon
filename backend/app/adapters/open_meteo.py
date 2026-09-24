from __future__ import annotations
from app.adapters.base import BaseAdapter
from app.config import settings

class OpenMeteoAdapter(BaseAdapter):
    name = "open_meteo"
    source_url = "https://open-meteo.com/"

    async def current(self, lat: float, lon: float):
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ",".join([
                "temperature_2m","relative_humidity_2m","precipitation","rain",
                "cloud_cover","wind_speed_10m","wind_direction_10m"
            ]),
            "hourly": ",".join([
                "temperature_2m","relative_humidity_2m","precipitation_probability",
                "precipitation","cloud_cover","soil_moisture_0_to_1cm","soil_moisture_1_to_3cm",
                "et0_fao_evapotranspiration"
            ]),
            "forecast_days": 3,
            "timezone": "Asia/Kolkata",
        }
        return await self.get_json(settings.open_meteo_url, params=params)

    async def historical_daily(self, lat: float, lon: float, start_date: str, end_date: str):
        params = {
            "latitude": lat, "longitude": lon, "start_date": start_date, "end_date": end_date,
            "daily": "temperature_2m_mean,precipitation_sum", "timezone": "Asia/Kolkata",
        }
        return await self.get_json(settings.open_meteo_archive_url, params=params)
