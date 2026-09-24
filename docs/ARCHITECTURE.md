# VanRakshak AI Architecture

## Core design rules

1. **Real data first** — provider failure is shown, never replaced with fake environmental values.
2. **Map first** — the India map is the main workspace; deep investigation opens contextually.
3. **Provider isolation** — every external system lives behind an adapter.
4. **Provenance first** — source, fetch time, observation time, freshness and resolution travel with results where relevant.
5. **Scientific honesty** — observed, derived, forecast and AI-estimated values remain distinct.
6. **Credential-safe** — secrets stay in environment variables/secret managers.
7. **Graceful degradation** — optional sources improve evidence but do not crash the core dashboard.

## Runtime topology

```text
                            ┌──────────────────────────────┐
                            │     VanRakshak Web UI        │
                            │ MapLibre • filters • compare │
                            │ timeline • profile • patrol  │
                            └──────────────┬───────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │        FastAPI          │
                              │ /api/* + provenance     │
                              └────────────┬────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
              ▼                            ▼                            ▼
   ┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
   │ Source adapters      │     │ Intelligence        │     │ Raster / tile path   │
   │ Copernicus           │     │ risk / doctor       │     │ Earth Search STAC    │
   │ Earth Search         │     │ cascade / recovery  │     │ Sentinel COG assets  │
   │ ASF Sentinel-1       │     │ prediction / carbon │     │ TiTiler              │
   │ FIRMS / Weather      │     │ fragmentation       │     │ NDVI/NDMI/NBR/NDWI   │
   │ Soil / OSM / GDELT   │     │ evidence chain      │     └─────────────────────┘
   │ GFW / EE / Bhuvan    │     └─────────────────────┘
   └──────────┬───────────┘
              │
              ▼
   ┌─────────────────────┐
   │ Persistence / jobs   │
   │ PostGIS / SQLAlchemy │
   │ Redis / Celery       │
   └─────────────────────┘
```

## Satellite path

### Discovery

- Copernicus Data Space STAC: Sentinel-2 catalogue metadata.
- Element 84 Earth Search: Sentinel-2 L2A public STAC items/COG assets.
- ASF: Sentinel-1 radar-scene discovery.

### Visual rendering

```text
Earth Search STAC item
       ↓
TiTiler STAC endpoint
       ↓
True color / false color / spectral expression
       ↓
MapLibre raster source
```

Supported map modes:

- true color
- false color
- NDVI
- NDMI
- NBR
- NDWI

### Before / after

The comparison endpoint selects scenes close to the user-selected dates and returns two tile specifications. The frontend displays two synchronized MapLibre maps with a draggable split.

### Time machine

The time-machine endpoint searches historical Sentinel-2 scenes, sorts them by observation time and lets the UI step/play through real image tiles.

## Remote change analysis

The working baseline uses source-backed Sentinel-2 pixels:

```text
Before + After Sentinel-2 L2A assets
               ↓
AOI read + common grid/resampling
               ↓
SCL cloud/shadow masking where available
               ↓
NDVI + NDMI + NBR + NDWI
               ↓
forest-conditioned vegetation decline screen
               ↓
loss candidate mask + polygons + hectares
               ↓
fragmentation before/after
               ↓
IsolationForest anomaly corroboration
               ↓
screening confidence + evidence
```

The baseline is intentionally labelled a **screening detector**, not a validated deep deforestation model.

## Optional Open-CD deep model

Open-CD is an upgrade path, not a fake pre-trained claim. The runtime status endpoint reports whether a config/checkpoint has been supplied.

Before enabling a deep model for judging, compare candidates such as TinyCD / Changer / ChangeFormer on geographic holdout regions and record:

- Precision
- Recall
- F1
- IoU / Dice
- false-positive rate
- inference time
- cloud/season robustness

## Earth Engine filter architecture

When Google Earth Engine authentication is configured, the layer registry exposes tile/value endpoints for datasets including:

- Dynamic World tree probability / labels
- Hansen forest cover/loss year
- SRTM elevation/slope/aspect
- JRC surface water occurrence
- MODIS land-surface temperature
- CHIRPS rainfall
- MODIS burned area
- GEDI L4A biomass
- WCMC biomass-carbon density reference
- WorldPop population
- Global Human Modification
- WDPA protected areas

Earth Engine is optional. A missing EE credential disables those layers visibly rather than breaking the map.

## Forest investigation path

```text
clicked/search location
      ↓
reverse geocode
      ↓
Sentinel-2 + Sentinel-1 availability
weather / climate anomaly
soil reference
FIRMS fire
OSM human pressure
GFW alerts
news context
protected-area / terrain / biomass when available
      ↓
multisource evidence chain
      ↓
Forest Doctor + warning + priority
      ↓
report / patrol / persistence
```

## Intelligence layer

- transparent risk score
- smart warning: Normal / Watch / Warning / Critical
- AI Forest Doctor probable-driver analysis
- threat cascade
- what-if scenarios
- recovery intelligence / exit conditions
- resilience score
- trend-based threat projection with uncertainty
- regional comparison
- climate–forest correlation
- carbon-impact estimation
- environmental anomaly radar

No model output is allowed to silently become a factual observation.

## Human-pressure / causation rule

OSM roads, settlements, quarry/mine features and news articles are **contextual evidence only**. VanRakshak does not accuse a person/entity or claim illegal activity from proximity/correlation.

## Patrol path

```text
priority alert points
    ↓
priority-aware ordering
    ↓
OSRM road route when available
    ↓
MapLibre patrol geometry
```

The API explicitly warns that forest-road/track mapping may be incomplete.

## Persistence and workers

Docker Compose provides:

- PostgreSQL/PostGIS
- Redis
- Celery worker
- Celery beat
- TiTiler
- FastAPI

Current persistence models include investigations, alerts and provider-health records. Heavy satellite processing can be moved to Celery without changing the client API contract.

## Frontend principles

- dark, clean command-center visual language
- large map first
- collapsible layer drawer
- advanced tools in modals/drawers
- no wall of cards
- source/freshness shown near evidence
- before/after and time machine are contextual tools

## Data-state labels

- `LIVE_NRT`
- `DYNAMIC_RECENT`
- `HISTORICAL`
- `REFERENCE`
- `FORECAST`
- `AI_ESTIMATE`

These are part of the product contract, not decorative labels.
