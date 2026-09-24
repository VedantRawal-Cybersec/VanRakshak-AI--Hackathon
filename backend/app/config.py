from __future__ import annotations
from dataclasses import dataclass
import os


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()

@dataclass(frozen=True)
class Settings:
    app_name: str = "VanRakshak AI"
    environment: str = _env("VANRAKSHAK_ENV", "development")
    request_timeout_s: float = float(_env("REQUEST_TIMEOUT_S", "20"))
    cache_ttl_s: int = int(_env("CACHE_TTL_S", "300"))
    firms_map_key: str = _env("FIRMS_MAP_KEY")
    protected_planet_token: str = _env("PROTECTED_PLANET_TOKEN")
    copernicus_stac_url: str = _env("COPERNICUS_STAC_URL", "https://stac.dataspace.copernicus.eu/v1")
    open_meteo_url: str = _env("OPEN_METEO_URL", "https://api.open-meteo.com/v1/forecast")
    open_meteo_archive_url: str = _env("OPEN_METEO_ARCHIVE_URL", "https://archive-api.open-meteo.com/v1/archive")
    soilgrids_url: str = _env("SOILGRIDS_URL", "https://rest.isric.org/soilgrids/v2.0/properties/query")
    overpass_url: str = _env("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
    gdelt_url: str = _env("GDELT_URL", "https://api.gdeltproject.org/api/v2/doc/doc")
    protected_planet_url: str = _env("PROTECTED_PLANET_URL", "https://api.protectedplanet.net/v4")
    earth_search_url: str = _env("EARTH_SEARCH_URL", "https://earth-search.aws.element84.com/v1")
    gibs_url: str = _env("GIBS_URL", "https://gibs.earthdata.nasa.gov")
    eonet_url: str = _env("EONET_URL", "https://eonet.gsfc.nasa.gov/api/v3")
    photon_url: str = _env("PHOTON_URL", "https://photon.komoot.io")
    nominatim_url: str = _env("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
    titiler_public_url: str = _env("TITILER_PUBLIC_URL", "http://localhost:8001")
    titiler_internal_url: str = _env("TITILER_INTERNAL_URL", "http://titiler:8000")
    google_cloud_project: str = _env("GOOGLE_CLOUD_PROJECT")
    database_url: str = _env("DATABASE_URL", "sqlite:///./vanrakshak.db")
    redis_url: str = _env("REDIS_URL", "redis://localhost:6379/0")
    osrm_url: str = _env("OSRM_URL", "https://router.project-osrm.org")
    bhuvan_wms_url: str = _env("BHUVAN_WMS_URL", "https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms")
    auto_init_db: bool = _env("AUTO_INIT_DB", "false").lower() in {"1", "true", "yes", "on"}
    allow_network: bool = _env("ALLOW_NETWORK", "true").lower() in {"1", "true", "yes", "on"}
    monitor_lat: float = float(_env("MONITOR_LAT", "12.3375"))
    monitor_lon: float = float(_env("MONITOR_LON", "75.8069"))

settings = Settings()
