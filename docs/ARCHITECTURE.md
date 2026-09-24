# Architecture

## Design goals

1. **Real-data first** — unavailable sources fail visibly; they never produce synthetic environmental values.
2. **Provider isolation** — every external source is behind an adapter.
3. **Provenance** — source, observation time, fetch time, freshness and resolution travel with the data.
4. **Map first** — the India map remains the primary interface; advanced details open contextually.
5. **Credential-safe** — secrets are environment variables only.
6. **Scalable path** — synchronous MVP adapters can move to Celery/Redis workers and PostGIS/PgSTAC without changing client contracts.

## Services

### Web
Static production-compatible command-center UI using MapLibre GL JS. For a larger team deployment this can be migrated to Next.js without changing the backend API contracts.

### API
FastAPI service exposing source adapters and intelligence functions.

### Database
Docker Compose includes PostGIS. The current MVP keeps source results transient; production ingestion should persist normalized alerts, AOIs, observation metadata and analysis results into PostGIS/PgSTAC.

### Worker path
Heavy imagery download, cloud masking, COG generation, Open-CD inference and time-series recomputation should run out-of-request in worker processes. Redis/Celery are the recommended path from the project spec.

## AI path

```text
Before scene + After scene
        ↓
registration / cloud masking
        ↓
NDVI/NDMI/NBR baselines
        ↓
Open-CD candidate models
        ↓
georeferenced change mask
        ↓
forest-specific validation
        ↓
polygon + area + confidence
        ↓
environmental evidence fusion
        ↓
risk / warning / explanation
```

Do not choose a final deep-learning model until TinyCD/Changer/ChangeFormer or equivalent candidates have been compared on geographic holdout areas.
