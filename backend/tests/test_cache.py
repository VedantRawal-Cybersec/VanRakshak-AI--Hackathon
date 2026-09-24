import asyncio
import time

from app.services import cache as cache_service


def test_cached_async_falls_back_to_memory_without_redis(monkeypatch):
    cache_service.clear_cache()
    monkeypatch.setattr(cache_service, "_redis_disabled_until", time.monotonic()+60)
    calls={"n":0}

    async def producer():
        calls["n"]+=1
        return {"value":42}

    first=asyncio.run(cache_service.cached_async("unit:test",60,producer))
    second=asyncio.run(cache_service.cached_async("unit:test",60,producer))
    assert first=={"value":42}
    assert second=={"value":42}
    assert calls["n"]==1
    stats=cache_service.cache_stats()
    assert stats["entries"]>=1
    assert stats["persistent_backend"]=="redis_with_memory_fallback"
