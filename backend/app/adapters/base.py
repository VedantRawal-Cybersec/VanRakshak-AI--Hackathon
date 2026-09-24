from __future__ import annotations
from datetime import datetime, timezone
import httpx
from app.config import settings

class AdapterError(RuntimeError):
    pass

class BaseAdapter:
    name = "base"
    source_url = ""

    async def _request(self, method: str, url: str, **kwargs):
        if not settings.allow_network:
            raise AdapterError("Network access disabled by ALLOW_NETWORK=false")
        timeout = httpx.Timeout(settings.request_timeout_s)
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={"User-Agent":"VanRakshakAI/2.0"}) as client:
                r = await client.request(method, url, **kwargs)
                r.raise_for_status()
                return r
        except httpx.TimeoutException as exc:
            raise AdapterError(f"{self.name or 'provider'} timed out") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response else "unknown"
            raise AdapterError(f"{self.name or 'provider'} returned HTTP {status}") from exc
        except httpx.RequestError as exc:
            raise AdapterError(f"{self.name or 'provider'} is unreachable: {exc}") from exc

    async def get_json(self, url: str, **kwargs):
        r = await self._request("GET", url, **kwargs)
        try:
            return r.json()
        except Exception as exc:
            raise AdapterError(f"{self.name or 'provider'} returned invalid JSON") from exc

    async def post_json(self, url: str, **kwargs):
        r = await self._request("POST", url, **kwargs)
        try:
            return r.json()
        except Exception as exc:
            raise AdapterError(f"{self.name or 'provider'} returned invalid JSON") from exc

    async def get_text(self, url: str, **kwargs):
        return (await self._request("GET", url, **kwargs)).text

    async def get_bytes(self, url: str, **kwargs):
        r = await self._request("GET", url, **kwargs)
        return r.content, (r.headers.get("content-type") or "application/octet-stream").split(";")[0]

    @staticmethod
    def now_iso():
        return datetime.now(timezone.utc).isoformat()
