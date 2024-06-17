import asyncio


class Cache:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.cache = {}

    async def get(self, key):
        async with self.lock:
            return self.cache.get(key)

    async def set(self, key, value):
        async with self.lock:
            self.cache[key] = value


cache = Cache()
