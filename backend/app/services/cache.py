from __future__ import annotations
import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

_store: dict[str, tuple[float, Any]] = {}
_locks: dict[str, asyncio.Lock] = {}
_guard = asyncio.Lock()

async def _lock_for(key: str) -> asyncio.Lock:
    async with _guard:
        lock=_locks.get(key)
        if lock is None:
            lock=asyncio.Lock()
            _locks[key]=lock
        return lock

async def cached_async(key: str, ttl_s: int, producer: Callable[[], Awaitable[Any]]):
    now=time.monotonic()
    hit=_store.get(key)
    if hit and hit[0] > now:
        return hit[1]
    lock=await _lock_for(key)
    async with lock:
        now=time.monotonic()
        hit=_store.get(key)
        if hit and hit[0] > now:
            return hit[1]
        value=await producer()
        _store[key]=(time.monotonic()+max(1,ttl_s),value)
        return value

def clear_cache(prefix: str | None = None):
    if prefix is None:
        _store.clear()
        return
    for k in list(_store):
        if k.startswith(prefix):
            _store.pop(k,None)

def cache_stats():
    now=time.monotonic()
    alive={k:v for k,v in _store.items() if v[0]>now}
    expired=len(_store)-len(alive)
    if expired:
        _store.clear(); _store.update(alive)
    return {"entries":len(alive),"expired_removed":expired}
