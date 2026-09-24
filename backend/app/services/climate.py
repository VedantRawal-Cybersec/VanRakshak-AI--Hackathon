from __future__ import annotations
from datetime import date, timedelta
import numpy as np

async def anomaly(open_meteo, lat: float, lon: float, window_days: int = 30, baseline_years: int = 5):
    # Archive API is intentionally used: anomalies must compare observations/reanalysis,
    # not a current forecast against an unrelated climatology.
    lag = 6  # archive/reanalysis products are not always available for the current day
    recent_end = date.today() - timedelta(days=lag)
    recent_start = recent_end - timedelta(days=window_days-1)
    base_start = recent_start.replace(year=recent_start.year-baseline_years)
    data = await open_meteo.historical_daily(lat, lon, base_start.isoformat(), recent_end.isoformat())
    daily = data.get("daily") or {}
    dates = daily.get("time") or []
    temps = daily.get("temperature_2m_mean") or []
    rain = daily.get("precipitation_sum") or []
    rows=[]
    for d,t,r in zip(dates,temps,rain):
        if t is None or r is None: continue
        rows.append((date.fromisoformat(d),float(t),float(r)))
    recent=[x for x in rows if recent_start<=x[0]<=recent_end]
    hist=[x for x in rows if x[0]<recent_start]
    if len(recent)<max(5,window_days//2) or len(hist)<30:
        raise ValueError("Not enough historical data returned to compute anomaly")
    recent_t=np.mean([x[1] for x in recent]); recent_r=np.sum([x[2] for x in recent])
    # Compare each historical year over the same month/day window.
    hist_t=[];hist_r=[]
    for y in range(recent_start.year-baseline_years,recent_start.year):
        try:
            s=recent_start.replace(year=y); e=recent_end.replace(year=y)
        except ValueError:
            continue
        yr=[x for x in hist if s<=x[0]<=e]
        if yr:
            hist_t.append(np.mean([x[1] for x in yr])); hist_r.append(np.sum([x[2] for x in yr]))
    if not hist_t or not hist_r: raise ValueError("Historical baseline windows unavailable")
    t_base=float(np.mean(hist_t)); r_base=float(np.mean(hist_r))
    rain_def=0 if r_base<=0 else max(-200,min(100,(r_base-recent_r)/r_base*100))
    return {
        "window":{"start":recent_start.isoformat(),"end":recent_end.isoformat(),"days":window_days},
        "temperature_mean_c":round(float(recent_t),2),"temperature_baseline_c":round(t_base,2),"temperature_anomaly_c":round(float(recent_t-t_base),2),
        "rainfall_sum_mm":round(float(recent_r),2),"rainfall_baseline_mm":round(r_base,2),"rainfall_deficit_pct":round(float(rain_def),1),
        "baseline_years":len(hist_t),"label":"DERIVED_METRIC","source":getattr(open_meteo,"climate_source","Open-Meteo Historical/Reanalysis"),
    }
