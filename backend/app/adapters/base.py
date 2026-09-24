from __future__ import annotations
from datetime import datetime, timezone
import asyncio
import hashlib
import json
import time
import httpx
from app.config import settings

class AdapterError(RuntimeError):
    pass

_CACHE: dict[str, tuple[float, object]] = {}
_CACHE_LOCK = asyncio.Lock()

def _stable(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        return repr(value)

def _cache_key(kind: str, url: str, kwargs: dict) -> str:
    relevant={k:v for k,v in kwargs.items() if k in {"params","json","data"}}
    raw=f"{kind}|{url}|{_stable(relevant)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

async def _cache_get(key: str):
    if settings.cache_ttl_s <= 0:
        return None, False
    async with _CACHE_LOCK:
        row=_CACHE.get(key)
        if not row:
            return None, False
        expires,value=row
        if expires < time.monotonic():
            _CACHE.pop(key,None)
            return None, False
        return value, True

async def _cache_put(key: str, value):
    if settings.cache_ttl_s <= 0:
        return
    async with _CACHE_LOCK:
        # Bound the in-process cache so a hackathon demo cannot grow indefinitely.
        if len(_CACHE) > 2048:
            now=time.monotonic()
            for k,(expires,_) in list(_CACHE.items())[:512]:
                if expires < now:
                    _CACHE.pop(k,None)
            if len(_CACHE) > 2048:
                for k in list(_CACHE)[:256]:
                    _CACHE.pop(k,None)
        _CACHE[key]=(time.monotonic()+settings.cache_ttl_s,value)

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
        key=_cache_key("GET_JSON",url,kwargs)
        value,hit=await _cache_get(key)
        if hit:
            return value
        r = await self._request("GET", url, **kwargs)
        try:
            value=r.json()
        except Exception as exc:
            raise AdapterError(f"{self.name or 'provider'} returned invalid JSON") from exc
        await _cache_put(key,value)
        return value

    async def post_json(self, url: str, **kwargs):
        key=_cache_key("POST_JSON",url,kwargs)
        value,hit=await _cache_get(key)
        if hit:
            return value
        r = await self._request("POST", url, **kwargs)
        try:
            value=r.json()
        except Exception as exc:
            raise AdapterError(f"{self.name or 'provider'} returned invalid JSON") from exc
        await _cache_put(key,value)
        return value

    async def get_text(self, url: str, **kwargs):
        key=_cache_key("GET_TEXT",url,kwargs)
        value,hit=await _cache_get(key)
        if hit:
            return value
        value=(await self._request("GET", url, **kwargs)).text
        await _cache_put(key,value)
        return value

    async def get_bytes(self, url: str, **kwargs):
        # Raster/image bytes are deliberately not cached in Python memory.
        r = await self._request("GET", url, **kwargs)
        return r.content, (r.headers.get("content-type") or "application/octet-stream").split(";")[0]

    @staticmethod
    def now_iso():
        return datetime.now(timezone.utc).isoformat()
