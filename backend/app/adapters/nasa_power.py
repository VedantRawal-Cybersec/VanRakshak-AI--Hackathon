from __future__ import annotations

from datetime import date, timedelta
from app.adapters.base import BaseAdapter, AdapterError
from app.config import settings


class NASAPowerAdapter(BaseAdapter):
    """Keyless NASA POWER daily meteorology adapter normalized to VanRakshak's climate schema."""

    name = "nasa_power"
    source_url = "https://power.larc.nasa.gov/"
    climate_source = "NASA POWER Daily Meteorology"

    async def historical_daily(self, lat: float, lon: float, start_date: str, end_date: str):
        try:
            start=date.fromisoformat(start_date)
            end=date.fromisoformat(end_date)
        except ValueError as exc:
            raise AdapterError("NASA POWER dates must use YYYY-MM-DD") from exc
        if end < start:
            raise AdapterError("NASA POWER end date must not be before start date")
        params={
            "parameters":"T2M,PRECTOTCORR",
            "community":"AG",
            "longitude":lon,
            "latitude":lat,
            "start":start.strftime("%Y%m%d"),
            "end":end.strftime("%Y%m%d"),
            "format":"JSON",
        }
        data=await self.get_json(settings.nasa_power_url,params=params)
        parameter=((data.get("properties") or {}).get("parameter") or {})
        temp=parameter.get("T2M") or {}
        rain=parameter.get("PRECTOTCORR") or {}
        dates=sorted(set(temp).intersection(rain))
        if not dates:
            raise AdapterError("NASA POWER returned no overlapping T2M/PRECTOTCORR observations")
        def clean(v):
            try:
                x=float(v)
                return None if x <= -900 else x
            except Exception:
                return None
        return {
            "daily":{
                "time":[f"{d[:4]}-{d[4:6]}-{d[6:8]}" for d in dates],
                "temperature_2m_mean":[clean(temp.get(d)) for d in dates],
                "precipitation_sum":[clean(rain.get(d)) for d in dates],
            },
            "source":"NASA POWER",
            "metadata":data.get("header") or {},
        }

    async def health(self):
        end=date.today()-timedelta(days=7)
        start=end-timedelta(days=2)
        data=await self.historical_daily(12.9716,77.5946,start.isoformat(),end.isoformat())
        return {"ok":bool((data.get("daily") or {}).get("time")),"service":"NASA POWER Daily Point API"}
