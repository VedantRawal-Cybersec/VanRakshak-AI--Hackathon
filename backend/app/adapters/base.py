from __future__ import annotations
from datetime import datetime, timezone
import httpx
from app.config import settings

class AdapterError(RuntimeError):
    pass

class BaseAdapter:
    name = "base"
    source_url = ""

    async def get_json(self, url: str, **kwargs):
        if not settings.allow_network:
            raise AdapterError("Network access disabled by ALLOW_NETWORK=false")
        timeout = httpx.Timeout(settings.request_timeout_s)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={"User-Agent":"VanRakshakAI/1.0"}) as client:
            r = await client.get(url, **kwargs)
            r.raise_for_status()
            return r.json()

    async def get_text(self, url: str, **kwargs):
        if not settings.allow_network:
            raise AdapterError("Network access disabled by ALLOW_NETWORK=false")
        timeout = httpx.Timeout(settings.request_timeout_s)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={"User-Agent":"VanRakshakAI/1.0"}) as client:
            r = await client.get(url, **kwargs)
            r.raise_for_status()
            return r.text

    @staticmethod
    def now_iso():
        return datetime.now(timezone.utc).isoformat()
