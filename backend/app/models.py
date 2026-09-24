from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Literal

Freshness = Literal["LIVE_NRT", "DYNAMIC_RECENT", "HISTORICAL", "REFERENCE", "FORECAST", "AI_ESTIMATE", "UNKNOWN"]

class Provenance(BaseModel):
    source: str
    observed_at: str | None = None
    fetched_at: str | None = None
    freshness: Freshness = "UNKNOWN"
    resolution_m: float | None = None
    source_url: str | None = None
    notes: str | None = None

class SourceResult(BaseModel):
    ok: bool
    data: Any = None
    provenance: Provenance
    error: str | None = None

class Coordinates(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)

class RiskInputs(BaseModel):
    ndvi_drop: float = Field(0, ge=0, le=1)
    temp_anomaly_c: float = Field(0, ge=0, le=10)
    rainfall_deficit_pct: float = Field(0, ge=0, le=100)
    fire_signal: float = Field(0, ge=0, le=1)
    protected_area: bool = False
    fragmentation_change: float = Field(0, ge=0, le=1)
    human_pressure: float = Field(0, ge=0, le=1)
    model_confidence: float = Field(0.5, ge=0, le=1)

class CarbonRequest(BaseModel):
    area_ha: float = Field(gt=0)
    biomass_t_per_ha: float = Field(gt=0)
    uncertainty_pct: float = Field(25, ge=0, le=100)

class PatrolPoint(BaseModel):
    id: str
    lat: float
    lon: float
    priority: float = Field(ge=0, le=100)

class PatrolRequest(BaseModel):
    start_lat: float
    start_lon: float
    points: list[PatrolPoint]

class WhatIfRequest(BaseModel):
    base: RiskInputs
    temperature_delta_c: float = 0
    rainfall_delta_pct: float = 0
    fire_delta: float = 0
    ndvi_delta: float = 0

class ForestDoctorInputs(BaseModel):
    ndvi_drop: float = Field(0, ge=0, le=1)
    landcover_to_crop: float = Field(0, ge=0, le=1)
    fire_signal: float = Field(0, ge=0, le=1)
    road_proximity_km: float | None = Field(None, ge=0)
    settlement_proximity_km: float | None = Field(None, ge=0)
    mining_or_quarry_nearby: bool = False
    drought_severity: float = Field(0, ge=0, le=1)
    radar_change: float = Field(0, ge=0, le=1)

class RecoveryInputs(BaseModel):
    ndvi_baseline: float = Field(ge=-1, le=1)
    ndvi_current: float = Field(ge=-1, le=1)
    forest_cover_baseline: float = Field(ge=0, le=1)
    forest_cover_current: float = Field(ge=0, le=1)
    soil_moisture_percentile: float = Field(ge=0, le=100)
    recent_fire: bool = False
    months_since_disturbance: int = Field(ge=0)

class CorrelationInputs(BaseModel):
    temperature: list[float]
    rainfall: list[float]
    ndvi: list[float]
    fire: list[float]
    forest_loss: list[float]

class RegionThreat(BaseModel):
    name: str
    risk: float = Field(ge=0, le=100)
    forest_loss_ha: float = Field(ge=0)
    fire_count: int = Field(ge=0)
    ndvi_drop: float = Field(ge=0, le=1)
    protected_area: bool = False

class RegionComparisonRequest(BaseModel):
    regions: list[RegionThreat]


class ThreatPredictionRequest(BaseModel):
    values: list[float]
    dates: list[str] | None = None
    steps: int = Field(3, ge=1, le=24)
    floor: float = 0
    ceiling: float = 100

class PersistInvestigationRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    place: str = "India"
    payload: dict[str, Any]
