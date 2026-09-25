# VanRakshak AI — Judging Evidence Pack

This document maps the live product to the DATUM marking criteria without inventing model accuracy or environmental measurements.

## Data-integrity rule

Production UI values must be one of:

1. **Observed/reference data** from a named provider with provenance and freshness.
2. **Derived metric** computed transparently from observed/reference data.
3. **Forecast / AI estimate** computed from real observations and explicitly labelled as an estimate.
4. **Hypothetical scenario** applied to a real baseline and explicitly labelled hypothetical.
5. **Unavailable** when the required source cannot be obtained.

Demo presets are not exposed in the production dashboard. Verified scenario manifests remain only as CI/preflight test fixtures.

## Criterion evidence

### Problem Understanding — 10 marks available

VanRakshak covers the complete operational problem rather than only visualizing satellite imagery:

**detect → quantify → explain → prioritize → alert → route patrol → collect field evidence → re-observe**

Evidence in product:
- real before/after Sentinel-2 or historical Landsat comparison
- candidate vegetation/forest-loss polygons and affected hectares
- NDVI/NDMI/NBR/NDWI screening
- fragmentation and vegetation condition
- protected-area, weather/climate, soil, fire and human-pressure context
- Alerts and Precision Patrol Planner
- post-intervention satellite verification targets

### Innovation — 15 marks available

Integrated differentiators:
- Forest Digital Profile
- AI Evidence Chain
- AI Forest Doctor
- explainable smart warning
- environmental intelligence
- threat forecast with uncertainty
- real temporal holdout backtesting
- carbon semantics that separate local mapped estimates from regional reference context
- fragmentation analysis
- protected-area context
- actionable response plan
- road-aware OSRM/OSM patrol routing
- real field photo/video evidence capture
- source-backed investigation PDF

### AI / Technical Implementation — 20 marks available

Production stack:
- FastAPI
- Sentinel-2 L2A via STAC catalogues
- Sentinel-1 GRD corroboration when matched scenes are readable
- TiTiler raster rendering
- multispectral change analysis
- IsolationForest anomaly corroboration
- robust ensemble forecasting
- PostGIS
- Redis + Celery
- MapLibre
- OSRM / OpenStreetMap routing
- automated CI and Browser E2E
- Railway production deployment

The optional OpenCD deep model is never described as trained/validated unless a real configuration, checkpoint and geographic-holdout metrics file are configured.

### Data Science & Model Quality — 15 marks available

Measured validation evidence shown by the product:
- real valid-pixel count after quality/cloud masking
- cloud-masked fraction
- transparent change-screening confidence
- IsolationForest candidate-overlap fraction
- independent Sentinel-1 cross-sensor corroboration when available
- prediction temporal holdout MAE
- prediction temporal holdout RMSE
- forecast interval coverage
- ensemble model disagreement

Important limitation:
- **Precision / Recall / F1 / IoU are not claimed without a labelled geographic ground-truth benchmark.**
- The product explicitly shows these as unavailable rather than inventing accuracy.

### Sustainability Impact — 20 marks available

Measured/derived impact surfaces:
- candidate affected area in hectares
- vegetation health / NDVI change
- forest fragmentation
- climate stress and rainfall deficit
- fire context
- protected-area intersection
- carbon impact only when location-specific mapped/field carbon density is available
- broad IPCC Tier-1 carbon values remain clearly separated as regional context only
- action plan and measurable follow-up success conditions
- recovery/re-observation workflow

### Prototype / Usability — 10 marks available

Working production functions include:
- place search
- map quick filters
- source-aware legends
- Before / After
- Forest Time Machine
- Analysis
- Environmental Intelligence
- Predictions
- Alerts
- Precision Patrol Planner
- real field photo/video attachment preview
- route on both patrol map and main map
- investigation PDF
- source health and provenance
- responsive scrolling and close controls

### Presentation & Q&A — 10 marks available

Recommended demo story:

1. Search/select a forest.
2. Show real source badge and provenance.
3. Compare real before/after satellite scenes.
4. Run Analysis: what happened, where, environmental context and impact.
5. Open Model Quality: show what is actually validated and what is not claimed.
6. Run Predictions: what is happening, why the model flags it, actions, impact and temporal holdout error.
7. Open Alerts.
8. Build Precision Patrol route.
9. Show real field photo/video evidence requirements.
10. Explain the next-satellite verification loop.

## Production credential status

The system is designed to operate without fabricating values when optional credentials are absent.

Preferred optional sources:
- NASA FIRMS MAP key — pixel-level NRT fire detections
- Protected Planet token — official protected-area API
- Google Earth Engine project/auth — Dynamic World, GEDI, WCMC carbon density and related enhancement layers

When these are not configured, public real sources/fallbacks remain clearly labelled and non-equivalent fallbacks are never presented as the preferred source.

## Judge-safe answers

**“What is your model accuracy?”**

VanRakshak does not invent a single accuracy number. It currently exposes real temporal holdout forecast error, optical quality diagnostics, anomaly overlap and cross-sensor corroboration. Precision/Recall/F1/IoU require a labelled geographic ground-truth benchmark and are shown as unavailable until such a benchmark exists.

**“Is the carbon value exact?”**

Only a location-specific mapped/field carbon-density source is displayed as selected-area carbon impact. A broad IPCC Tier-1 estimate, when used, is shown separately as regional reference context and is not called a local measurement.

**“Is this live satellite video?”**

No. It is the newest available provider observation with real timestamps and freshness. Satellite archives are not described as continuous live video.

**“Does a probable driver prove illegal deforestation?”**

No. Probable drivers are evidence-ranked hypotheses for patrol verification. Field evidence and competent authority review are required for a factual/legal determination.
