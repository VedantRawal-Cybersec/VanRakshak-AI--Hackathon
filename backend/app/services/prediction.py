from __future__ import annotations
from datetime import date
import numpy as np
from app.models import ThreatPredictionRequest

def predict(req: ThreatPredictionRequest):
    if len(req.values) < 3:
        raise ValueError("At least 3 historical values are required")
    if req.dates and len(req.dates) != len(req.values):
        raise ValueError("dates and values must have equal length")
    y = np.asarray(req.values, dtype=float)
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    steps = max(1, min(req.steps, 24))
    future_x = np.arange(len(y), len(y)+steps, dtype=float)
    raw = intercept + slope * future_x
    lo = float(req.floor); hi = float(req.ceiling)
    vals = [round(float(np.clip(v, lo, hi)), 3) for v in raw]
    # residual spread provides a simple transparent uncertainty band.
    fitted = intercept + slope*x
    sigma = float(np.std(y - fitted)) if len(y) > 2 else 0.0
    return {
        "projected_values": vals,
        "trend_per_step": round(float(slope), 4),
        "uncertainty_sigma": round(sigma, 4),
        "lower": [round(float(np.clip(v-1.96*sigma, lo, hi)), 3) for v in raw],
        "upper": [round(float(np.clip(v+1.96*sigma, lo, hi)), 3) for v in raw],
        "method": "linear trend baseline with residual uncertainty",
        "label": "AI_ESTIMATE",
        "warning": "This is a risk projection baseline, not a guaranteed future event. Replace/benchmark with a validated temporal model when training data is available.",
    }
