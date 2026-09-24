# Deployment Guide

## Local / demo deployment

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up --build
```

Services:

- VanRakshak API/UI: `http://localhost:8000`
- FastAPI docs: `http://localhost:8000/docs`
- TiTiler: `http://localhost:8001`
- PostgreSQL/PostGIS: `localhost:5432`
- Redis: `localhost:6379`

## Required configuration

The application starts without optional provider secrets. Add only the services required for the demo:

```env
FIRMS_MAP_KEY=
PROTECTED_PLANET_TOKEN=
GOOGLE_CLOUD_PROJECT=
GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcp-service-account.json
```

Do not commit `.env` or credential files.

### NASA FIRMS

Put the MAP key in the runtime environment as `FIRMS_MAP_KEY`. The public repository must contain only the empty placeholder in `.env.example`.

Windows PowerShell:

```powershell
$env:FIRMS_MAP_KEY="<your FIRMS MAP key>"
```

Linux/macOS:

```bash
export FIRMS_MAP_KEY="<your FIRMS MAP key>"
```

Then verify with `GET /api/fire?lat=12.97&lon=77.59&days=1` or `GET /api/source-health`.

### Google Earth Engine

VanRakshak uses Google's official client: https://github.com/google/earthengine-api

You still need an Earth Engine-enabled Google Cloud project and authentication:

```env
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

The application verifies Earth Engine through `/api/source-health` and exposes configured catalog layers through `/api/earth-engine/catalog`.

## External network requirements

The API needs outbound HTTPS access to the enabled providers. The browser also needs access to MapLibre/OpenStreetMap CDN/base tiles unless those assets are self-hosted.

## Production hardening after hackathon

- Put API/UI behind HTTPS and a reverse proxy.
- Use a managed PostgreSQL/PostGIS database and managed Redis where possible.
- Persist alert/investigation jobs and run raster work asynchronously.
- Put generated COGs in durable object storage.
- Replace the public demo OSRM endpoint with a dedicated routing service for sustained use.
- Add authenticated users/roles if operational data should not be public.
- Add retention policies for generated imagery and reports.
- Add observability and source-health alerting.
