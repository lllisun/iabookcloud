from functools import lru_cache
from datetime import timedelta

def create_timed_lru_cache(seconds: int, maxsize: int):
    return lru_cache(maxsize=maxsize, typed=False)

cache = create_timed_lru_cache(seconds=3600, maxsize=100) # 1 hour of cache time, do i need to switch caching types once i deploy?