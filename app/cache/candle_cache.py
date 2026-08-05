from datetime import datetime, timedelta


class CandleCache:
    def __init__(self):
        self._cache = {}

    def get(self, key):
        item = self._cache.get(key)

        if item is None:
            return None

        expires_at, data = item

        if datetime.now() > expires_at:
            del self._cache[key]
            return None

        return data

    def set(self, key, data, ttl_seconds=60):
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

        self._cache[key] = (
            expires_at,
            data,
        )


cache = CandleCache()