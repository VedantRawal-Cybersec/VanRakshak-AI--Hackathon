from __future__ import annotations
import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

from app.config import settings

_store: dict[str, tuple[float, Any]] = {}
_locks: dict[str, asyncio.Lock] = {}
_guard = asyncio.Lock()
_redis_client = None
_redis_disabled_until = 0.0
_redis_last_ok: bool | None = None
_redis_last_error: str | None = None
_REDIS_PREFIX = "vanrakshak:cache:"


async def _lock_for(key: str) -> asyncio.Lock:
    async with _guard:
        lock=_locks.get(key)
        if lock is None:
            lock=asyncio.Lock()
            _locks[key]=lock
        return lock


async def _redis():
    global _redis_client, _redis_disabled_until, _redis_last_ok, _redis_last_error
    if not settings.redis_url or time.monotonic() < _redis_disabled_until:
        return None
    if _redis_client is None:
        try:
            import redis.asyncio as redis_async
            _redis_client=redis_async.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.8,
                health_check_interval=30,
            )
        except Exception as exc:
            _redis_last_ok=False
            _redis_last_error=str(exc)
            _redis_disabled_until=time.monotonic()+30
            return None
    return _redis_client


async def _redis_get(key: str):
    global _redis_disabled_until, _redis_last_ok, _redis_last_error
    client=await _redis()
    if client is None:
        return None
    try:
        raw=await client.get(_REDIS_PREFIX+key)
        _redis_last_ok=True
        _redis_last_error=None
        return json.loads(raw) if raw is not None else None
    except Exception as exc:
        _redis_last_ok=False
        _redis_last_error=str(exc)
        _redis_disabled_until=time.monotonic()+30
        return None


async def _redis_set(key: str, ttl_s: int, value: Any):
    global _redis_disabled_until, _redis_last_ok, _redis_last_error
    client=await _redis()
    if client is None:
        return
    try:
        raw=json.dumps(value,ensure_ascii=False,separators=(",",":"),default=str)
        await client.set(_REDIS_PREFIX+key,raw,ex=max(1,int(ttl_s)))
        _redis_last_ok=True
        _redis_last_error=None
    except Exception as exc:
        _redis_last_ok=False
        _redis_last_error=str(exc)
        _redis_disabled_until=time.monotonic()+30


async def redis_ping() -> dict:
    global _redis_disabled_until, _redis_last_ok, _redis_last_error
    client=await _redis()
    if client is None:
        return {"ok":False,"error":_redis_last_error or "Redis unavailable/backoff active"}
    try:
        started=time.perf_counter()
        ok=bool(await client.ping())
        _redis_last_ok=ok
        _redis_last_error=None if ok else "PING returned false"
        return {"ok":ok,"latency_ms":round((time.perf_counter()-started)*1000,1)}
    except Exception as exc:
        _redis_last_ok=False
        _redis_last_error=str(exc)
        _redis_disabled_until=time.monotonic()+30
        return {"ok":False,"error":str(exc)}


async def cached_async(key: str, ttl_s: int, producer: Callable[[], Awaitable[Any]]):
    now=time.monotonic()
    hit=_store.get(key)
    if hit and hit[0] > now:
        return hit[1]

    persistent=await _redis_get(key)
    if persistent is not None:
        _store[key]=(time.monotonic()+max(1,ttl_s),persistent)
        return persistent

    lock=await _lock_for(key)
    async with lock:
        now=time.monotonic()
        hit=_store.get(key)
        if hit and hit[0] > now:
            return hit[1]
        persistent=await _redis_get(key)
        if persistent is not None:
            _store[key]=(time.monotonic()+max(1,ttl_s),persistent)
            return persistent
        value=await producer()
        _store[key]=(time.monotonic()+max(1,ttl_s),value)
        await _redis_set(key,ttl_s,value)
        return value


def clear_cache(prefix: str | None = None):
    if prefix is None:
        _store.clear()
        return
    for k in list(_store):
        if k.startswith(prefix):
            _store.pop(k,None)


async def clear_cache_async(prefix: str | None = None):
    clear_cache(prefix)
    client=await _redis()
    if client is None:
        return
    pattern=_REDIS_PREFIX+(prefix or "")+"*"
    try:
        keys=[]
        async for key in client.scan_iter(match=pattern,count=250):
            keys.append(key)
            if len(keys)>=250:
                await client.delete(*keys); keys=[]
        if keys:
            await client.delete(*keys)
    except Exception:
        pass


def cache_stats():
    now=time.monotonic()
    alive={k:v for k,v in _store.items() if v[0]>now}
    expired=len(_store)-len(alive)
    if expired:
        _store.clear(); _store.update(alive)
    return {
        "entries":len(alive),
        "expired_removed":expired,
        "persistent_backend":"redis_with_memory_fallback",
        "redis_last_ok":_redis_last_ok,
        "redis_backoff_active":time.monotonic()<_redis_disabled_until,
        "redis_last_error":_redis_last_error,
    }
