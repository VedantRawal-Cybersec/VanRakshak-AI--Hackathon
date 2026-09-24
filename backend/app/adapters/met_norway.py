from __future__ import annotations

from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings


class METNorwayAdapter(BaseAdapter):
    """Credential-free global current/forecast fallback from MET Norway."""

    name = "met_norway"
    source_url = "https://api.met.no/weatherapi/locationforecast/2.0/"

    async def current(self, lat: float, lon: float):
        data = await self.get_json(
            settings.met_norway_url,
            params={"lat": lat, "lon": lon},
            headers={
                "User-Agent": "VanRakshakAI/2.0 (+https://github.com/VedantRawal-Cybersec/VanRakshak-AI--Hackathon)"
            },
        )
        series = ((data.get("properties") or {}).get("timeseries") or [])
        if not series:
            raise AdapterError("MET Norway returned no forecast timeseries")
        first = series[0]
        instant = (((first.get("data") or {}).get("instant") or {}).get("details") or {})
        next1 = (((first.get("data") or {}).get("next_1_hours") or {}).get("details") or {})
        rain = next1.get("precipitation_amount")
        current = {
            "time": first.get("time"),
            "temperature_2m": instant.get("air_temperature"),
            "relative_humidity_2m": instant.get("relative_humidity"),
            "precipitation": rain,
            "rain": rain,
            "cloud_cover": instant.get("cloud_area_fraction"),
            "wind_speed_10m": (
                None if instant.get("wind_speed") is None
                else round(float(instant["wind_speed"]) * 3.6, 2)
            ),
            "wind_direction_10m": instant.get("wind_from_direction"),
        }
        return {
            "latitude": ((data.get("geometry") or {}).get("coordinates") or [lon, lat])[1],
            "longitude": ((data.get("geometry") or {}).get("coordinates") or [lon, lat])[0],
            "current": current,
            "source": "MET Norway Locationforecast",
            "note": "Credential-free operational weather fallback; wind converted from m/s to km/h.",
        }

    async def health(self):
        data = await self.current(12.9716, 77.5946)
        return {"ok": bool((data.get("current") or {}).get("time")), "service": "MET Norway Locationforecast"}
