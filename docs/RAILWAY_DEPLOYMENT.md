# Railway Production Deployment

VanRakshak is prepared for Railway as a multi-service deployment.

## Required services

Create these services inside one Railway project:

1. **api** — this repository, Dockerfile `backend/Dockerfile`
2. **worker** — same repository/build, start command:
   `celery -A app.tasks.celery worker --loglevel=INFO`
3. **beat** — same repository/build, start command:
   `celery -A app.tasks.celery beat --loglevel=INFO`
4. **PostgreSQL** — Railway PostgreSQL plugin; enable PostGIS if the selected image/service supports it, otherwise current SQLAlchemy tables still work without spatial columns.
5. **Redis** — Railway Redis
6. **TiTiler** — a separate Railway service using `ghcr.io/developmentseed/titiler:latest`, public domain enabled.

## Shared environment

Set on api/worker/beat:

```env
VANRAKSHAK_ENV=production
ALLOW_NETWORK=true
AUTO_INIT_DB=true
CACHE_TTL_S=300
DATABASE_URL=<Railway PostgreSQL SQLAlchemy URL>
REDIS_URL=<Railway Redis URL>
TITILER_PUBLIC_URL=https://<titiler-public-domain>
TITILER_INTERNAL_URL=https://<titiler-public-domain>
MONITOR_LAT=12.3375
MONITOR_LON=75.8069
```

Optional enhancements:

```env
FIRMS_MAP_KEY=
PROTECTED_PLANET_TOKEN=
GOOGLE_CLOUD_PROJECT=
GOOGLE_APPLICATION_CREDENTIALS=
```

The project remains operational through public fallbacks when those optional credentials are absent.

## Health gates

- `GET /api/health` — process/config health
- `GET /api/ready` — application/database/static readiness
- `GET /api/source-health` — live provider telemetry
- `GET /api/fallbacks/status` — primary/fallback strategy
- `GET /api/cache/status` — request-cache state

## After deployment

Run:

```bash
BASE_URL=https://<api-domain> npm run e2e
```

and verify the GitHub **Public Provider Smoke**, **Demo Forest Preflight**, **Browser E2E**, and **CI** workflows are green.

Do not claim a provider is live merely because the code path exists; use `/api/source-health` and the provider-smoke workflows as the demo truth source.
