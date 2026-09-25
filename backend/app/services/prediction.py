from __future__ import annotations
from datetime import datetime, timedelta, timezone
import math
import numpy as np
from app.models import ThreatPredictionRequest


def _dates_axis(dates: list[str] | None, count: int):
    if not dates:
        return np.arange(count, dtype=float), None, None
    if len(dates) != count:
        raise ValueError("dates and values must have equal length")
    parsed=[]
    for raw in dates:
        try:
            parsed.append(datetime.fromisoformat(str(raw).replace("Z","+00:00")))
        except Exception as exc:
            raise ValueError("dates must use ISO/ YYYY-MM-DD values") from exc
    parsed=[x.replace(tzinfo=timezone.utc) if x.tzinfo is None else x for x in parsed]
    order=np.argsort(np.array([x.timestamp() for x in parsed]))
    parsed=[parsed[int(i)] for i in order]
    x=np.array([(d-parsed[0]).total_seconds()/86400.0 for d in parsed],dtype=float)
    return x, parsed, order


def _theil_sen(x: np.ndarray, y: np.ndarray):
    slopes=[]
    for i in range(len(y)):
        for j in range(i+1,len(y)):
            dx=float(x[j]-x[i])
            if abs(dx)>1e-9:
                slopes.append(float((y[j]-y[i])/dx))
    slope=float(np.median(slopes)) if slopes else 0.0
    return slope,float(np.median(y-slope*x))


def _fit_line(x: np.ndarray, y: np.ndarray, weights=None):
    if np.ptp(x)<=1e-12:
        return 0.0,float(np.mean(y))
    slope,intercept=np.polyfit(x,y,1,w=weights)
    return float(slope),float(intercept)


def _level(value: float, lo: float, hi: float):
    p=(value-lo)/max(1e-9,hi-lo)
    if p>=.75: return "VERY HIGH"
    if p>=.50: return "HIGH"
    if p>=.25: return "MODERATE"
    return "LOW"


def predict(req: ThreatPredictionRequest):
    if len(req.values)<3:
        raise ValueError("At least 3 historical values are required")
    lo=float(req.floor); hi=float(req.ceiling)
    if not math.isfinite(lo) or not math.isfinite(hi) or hi<=lo:
        raise ValueError("ceiling must be greater than floor")
    y=np.asarray(req.values,dtype=float)
    if not np.all(np.isfinite(y)):
        raise ValueError("values must all be finite numbers")
    x,parsed,order=_dates_axis(req.dates,len(y))
    if order is not None:
        y=y[order]
    steps=max(1,min(int(req.steps),24))
    gaps=np.diff(x) if len(x)>1 else np.array([],dtype=float)
    positive_gaps=gaps[gaps>0]
    cadence=float(np.median(positive_gaps)) if len(positive_gaps) else 1.0

    ols_s,ols_i=_fit_line(x,y)
    robust_s,robust_i=_theil_sen(x,y)
    weighted_s,weighted_i=_fit_line(x,y,np.sqrt(np.linspace(.55,1.65,len(y))))
    future_x=x[-1]+cadence*np.arange(1,steps+1,dtype=float)
    obs_models=np.vstack([ols_i+ols_s*x,robust_i+robust_s*x,weighted_i+weighted_s*x])
    future_models=np.vstack([ols_i+ols_s*future_x,robust_i+robust_s*future_x,weighted_i+weighted_s*future_x])
    fit=np.average(obs_models,axis=0,weights=[.35,.35,.30])
    raw=np.average(future_models,axis=0,weights=[.35,.35,.30])

    residual=y-fit
    sigma=float(np.std(residual,ddof=1)) if len(y)>3 else float(np.std(residual))
    model_spread=np.std(future_models,axis=0)
    horizon=np.arange(1,steps+1,dtype=float)
    uncertainty=np.sqrt(np.maximum(0,sigma*sigma)+model_spread*model_spread)*np.sqrt(1+horizon/max(3,len(y)))
    band=1.96*uncertainty
    projected=np.clip(raw,lo,hi); lower=np.clip(raw-band,lo,hi); upper=np.clip(raw+band,lo,hi)

    ss_res=float(np.sum((y-fit)**2)); ss_tot=float(np.sum((y-np.mean(y))**2))
    r2=1.0-ss_res/ss_tot if ss_tot>1e-12 else 1.0
    rmse=float(np.sqrt(np.mean((y-fit)**2))); mae=float(np.mean(np.abs(y-fit)))
    value_span=max(hi-lo,float(np.ptp(y)),1.0)
    trend_per_step=float(np.mean([ols_s,robust_s,weighted_s])*cadence)
    disagreement=float(np.mean(np.std(obs_models,axis=0)))
    volume=min(1.0,len(y)/10.0); fit_quality=max(0.0,min(1.0,r2))
    stability=max(0.0,1.0-min(1.0,rmse/value_span*4.0)); agreement=max(0.0,1.0-min(1.0,disagreement/value_span*6.0))
    confidence=round(100*(.25*volume+.35*fit_quality+.25*stability+.15*agreement),1)

    threshold=max(.35,value_span*.005)
    direction="INCREASING" if trend_per_step>threshold else "DECREASING" if trend_per_step<-threshold else "STABLE"
    strength_abs=abs(trend_per_step)/max(1.0,value_span)
    strength="STRONG" if strength_abs>=.08 else "MODERATE" if strength_abs>=.03 else "WEAK"
    forecast_dates=[(parsed[-1]+timedelta(days=cadence*h)).date().isoformat() for h in range(1,steps+1)] if parsed else []
    rows=[{"step":i+1,"date":forecast_dates[i] if forecast_dates else None,"projected":round(float(projected[i]),3),"lower":round(float(lower[i]),3),"upper":round(float(upper[i]),3)} for i in range(steps)]
    latest=float(y[-1]); final=float(projected[-1])
    summary=f"Series is {direction.lower()} ({strength.lower()} trend). Latest value {latest:.1f}; forecast step {steps} is {final:.1f} with {confidence:.0f}% model confidence."
    return {
        "projected_values":[round(float(v),3) for v in projected],"forecast_dates":forecast_dates,"forecast":rows,
        "trend_per_step":round(trend_per_step,4),"trend_per_day":round(float(np.mean([ols_s,robust_s,weighted_s])),6) if parsed else None,
        "uncertainty_sigma":round(sigma,4),"lower":[round(float(v),3) for v in lower],"upper":[round(float(v),3) for v in upper],
        "analysis":{"direction":direction,"strength":strength,"confidence_pct":confidence,"latest_value":round(latest,3),"forecast_final":round(final,3),"forecast_change":round(final-latest,3),"observed_change":round(float(y[-1]-y[0]),3),"recent_change":round(float(y[-1]-y[-2]),3),"risk_level":_level(final,lo,hi),"r2":round(r2,4),"rmse":round(rmse,4),"mae":round(mae,4),"observations":len(y),"cadence_days":round(cadence,1) if parsed else None,"summary":summary},
        "diagnostics":{"models":{"ordinary_linear":{"slope":round(ols_s,6),"weight":.35},"theil_sen_robust":{"slope":round(robust_s,6),"weight":.35},"recency_weighted":{"slope":round(weighted_s,6),"weight":.30}},"model_disagreement":round(disagreement,4),"observed_min":round(float(np.min(y)),3),"observed_max":round(float(np.max(y)),3)},
        "pipeline":["Validate and order the observed time series","Fit ordinary, robust Theil-Sen and recency-weighted trends","Blend model forecasts to reduce single-line sensitivity","Estimate uncertainty from residual error plus model disagreement","Generate dated forecast points and explainable trend diagnostics"],
        "method":"ensemble of ordinary linear, Theil-Sen robust, and recency-weighted trends with residual/model-disagreement uncertainty","label":"AI_ESTIMATE","generated_at":datetime.now(timezone.utc).isoformat(),
        "warning":"Projection extrapolates observed trends; it is not a guaranteed event or a probability of illegal deforestation.",
    }
