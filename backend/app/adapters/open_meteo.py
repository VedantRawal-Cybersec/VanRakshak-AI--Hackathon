from __future__ import annotations
import math
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

    async def terrain(self, lat: float, lon: float, spacing_m: float = 180.0):
        """Derive local slope/aspect from real Copernicus DEM elevation samples.

        Open-Meteo's public Elevation API serves Copernicus DEM GLO-90 data.
        Five samples (center/west/east/south/north) are used for a transparent
        central-difference terrain estimate. This is a real DEM-derived metric,
        not a fabricated fallback.
        """
        spacing=max(90.0,min(float(spacing_m),1000.0))
        lat_step=spacing/111_320.0
        lon_scale=max(0.15,abs(math.cos(math.radians(float(lat)))))
        lon_step=spacing/(111_320.0*lon_scale)
        pts=[
            (float(lat),float(lon)),
            (float(lat),float(lon)-lon_step),
            (float(lat),float(lon)+lon_step),
            (float(lat)-lat_step,float(lon)),
            (float(lat)+lat_step,float(lon)),
        ]
        data=await self.get_json(
            "https://api.open-meteo.com/v1/elevation",
            params={
                "latitude": ",".join(f"{p[0]:.7f}" for p in pts),
                "longitude": ",".join(f"{p[1]:.7f}" for p in pts),
            },
        )
        elevations=data.get("elevation") if isinstance(data,dict) else None
        if not isinstance(elevations,list) or len(elevations)!=5 or any(x is None for x in elevations):
            raise ValueError("Open-Meteo Elevation API did not return the five required DEM samples")
        center,west,east,south,north=[float(x) for x in elevations]
        dzdx=(east-west)/(2.0*spacing)
        dzdy=(north-south)/(2.0*spacing)
        slope=math.degrees(math.atan(math.sqrt(dzdx*dzdx+dzdy*dzdy)))
        # Downslope azimuth, clockwise from north.
        aspect=(math.degrees(math.atan2(-dzdx,-dzdy))+360.0)%360.0
        return {
            "elevation_m":round(center,1),
            "slope_deg":round(slope,2),
            "aspect_deg":round(aspect,1),
            "spacing_m":spacing,
            "dem_resolution_m":90,
            "samples":{
                "center":center,"west":west,"east":east,"south":south,"north":north,
            },
            "source":"Open-Meteo Elevation API / Copernicus DEM GLO-90",
            "source_url":"https://open-meteo.com/en/docs/elevation-api",
            "method":"5-point central-difference slope/aspect from Copernicus DEM elevation samples",
            "label":"DERIVED_METRIC",
        }
