from __future__ import annotations
import time
from typing import Any

class TTLCache:
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str):
        item = self._store.get(key)
        if not item:
            return None
        expires, value = item
        if expires < time.time():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: int | None = None):
        self._store[key] = (time.time() + (ttl or self.ttl), value)
        return value

cache = TTLCache()
