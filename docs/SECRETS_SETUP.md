# Provider Secrets Setup

VanRakshak keeps provider credentials out of Git history. The public repository must never contain the real NASA FIRMS MAP key, Google service-account JSON, Protected Planet token, or other private credentials.

## NASA FIRMS

The application already reads:

```env
FIRMS_MAP_KEY=<your-map-key>
```

Local development:

1. Copy `.env.example` to `.env`.
2. Put the real key only in the local `.env`.
3. Never commit `.env`.

GitHub Actions / hosted deployment:

1. Repository → **Settings** → **Secrets and variables** → **Actions**.
2. Create repository secret named `FIRMS_MAP_KEY`.
3. Paste the key there.
4. Run **Provider Smoke Test** from the Actions tab.

## Google Earth Engine

Official client repository:

- https://github.com/google/earthengine-api

Python dependency used by VanRakshak:

```text
earthengine-api
```

The backend initializes Earth Engine from Application Default Credentials / a Google service-account credential file and a Cloud project.

Local environment:

```env
GOOGLE_CLOUD_PROJECT=<your-ee-enabled-project-id>
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
```

GitHub Actions:

- `GOOGLE_CLOUD_PROJECT` — repository secret containing the Earth Engine-enabled Google Cloud project ID.
- `GEE_SERVICE_ACCOUNT_JSON` — repository secret containing the complete service-account JSON. The provider-smoke workflow writes it to a temporary runner file; it is never committed.

Your Google Cloud project/service account must be registered/authorized for Earth Engine according to Google's current Earth Engine access requirements.

## Protected Planet

```env
PROTECTED_PLANET_TOKEN=<token>
```

Store it as a local environment variable or hosted deployment secret, never in source control.

## Validation

Run:

```bash
python scripts/check_secrets.py
```

GitHub CI runs this check on every push and pull request.

The scheduled/manual `Provider Smoke Test` validates credential-gated providers only when the matching GitHub secrets are configured.
