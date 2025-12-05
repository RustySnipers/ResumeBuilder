"""
Redis Cache Configuration - Phase 2.1

This module provides Redis connection pooling and caching utilities for the Resume Builder application.

Features:
- Connection pooling with configurable pool size
- TTL-based caching policies
- Cache invalidation strategies
- JSON serialization for complex objects
"""

import json
import os
import time
from typing import Optional, Any, Dict
import fnmatch

from backend.config import is_lite_mode

# ============================================================================
# Redis Configuration
# ============================================================================

LITE_MODE = is_lite_mode()

if not LITE_MODE:
    import redis.asyncio as aioredis
else:
    aioredis = None

# Redis URL from environment variable with fallback to local development
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Default TTL values (in seconds)
DEFAULT_TTL = 3600  # 1 hour
ANALYSIS_TTL = 3600  # 1 hour for analysis results
RESUME_TTL = 1800  # 30 minutes for resume data
JOB_DESC_TTL = 1800  # 30 minutes for job descriptions

if not LITE_MODE:
    redis_pool = aioredis.ConnectionPool.from_url(
        REDIS_URL,
        max_connections=10,
        decode_responses=False,
    )
else:
    redis_pool = None

redis_client: Optional[Any] = None


class _InMemoryCache:
    """Simple in-memory stand-in for Redis when Lite Mode is enabled."""

    def __init__(self):
        self.store: Dict[str, tuple[str, float]] = {}

    async def get(self, key: str) -> Optional[str]:
        value = self.store.get(key)
        if not value:
            return None
        data, expires_at = value
        if expires_at and expires_at < time.time():
            self.store.pop(key, None)
            return None
        return data

    async def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        expires_at = time.time() + ttl_seconds if ttl_seconds else 0
        self.store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def scan_iter(self, match: str):
        for key in list(self.store.keys()):
            if fnmatch.fnmatch(key, match):
                yield key

    async def ping(self):
        return True

    async def close(self):
        self.store.clear()


# ============================================================================
# Connection Management
# ============================================================================

async def init_redis() -> None:
    """
    Initialize Redis connection pool.

    Call this during application startup to establish Redis connections.
    """
    global redis_client
    if LITE_MODE:
        redis_client = _InMemoryCache()
    else:
        redis_client = aioredis.Redis(connection_pool=redis_pool)


async def close_redis() -> None:
    """
    Close Redis connection pool.

    Call this during application shutdown to ensure clean connection closure.
    """
    if redis_client:
        if hasattr(redis_client, "close"):
            await redis_client.close()
    if redis_pool:
        await redis_pool.disconnect()


async def check_redis_health() -> bool:
    """
    Check if Redis is accessible and healthy.

    Returns:
        bool: True if Redis is accessible, False otherwise
    """
    try:
        if redis_client is None:
            return False
        await redis_client.ping()
        return True
    except Exception:
        return False


# ============================================================================
# Caching Utilities
# ============================================================================

async def get_cache(key: str) -> Optional[Any]:
    """
    Get value from Redis cache.

    Args:
        key: Cache key

    Returns:
        Cached value (deserialized from JSON) or None if not found/expired
    """
    if redis_client is None:
        return None

    try:
        value = await redis_client.get(key)
        if value is None:
            return None

        # Deserialize JSON
        return json.loads(value)
    except Exception as e:
        # Log error in production
        print(f"Redis get error for key {key}: {e}")
        return None


async def set_cache(
    key: str, value: Any, ttl: Optional[int] = None
) -> bool:
    """
    Set value in Redis cache with TTL.

    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        ttl: Time-to-live in seconds (default: DEFAULT_TTL)

    Returns:
        bool: True if successful, False otherwise
    """
    if redis_client is None:
        return False

    try:
        serialized = json.dumps(value)
        ttl_seconds = ttl or DEFAULT_TTL
        await redis_client.setex(key, ttl_seconds, serialized)
        return True
    except Exception as e:
        print(f"Redis set error for key {key}: {e}")
        return False


async def delete_cache(key: str) -> bool:
    """
    Delete value from Redis cache.

    Args:
        key: Cache key to delete

    Returns:
        bool: True if successful, False otherwise
    """
    if redis_client is None:
        return False

    try:
        await redis_client.delete(key)
        return True
    except Exception as e:
        print(f"Redis delete error for key {key}: {e}")
        return False


async def delete_pattern(pattern: str) -> int:
    """
    Delete all keys matching a pattern.

    Args:
        pattern: Pattern to match (e.g., "user:123:*")

    Returns:
        int: Number of keys deleted
    """
    if redis_client is None:
        return 0

    try:
        count = 0
        async for key in redis_client.scan_iter(match=pattern):
            await redis_client.delete(key)
            count += 1
        return count
    except Exception as e:
        print(f"Redis delete pattern error for {pattern}: {e}")
        return 0


async def cache_exists(key: str) -> bool:
    """
    Check if a cache key exists.

    Args:
        key: Cache key to check

    Returns:
        bool: True if key exists, False otherwise
    """
    if redis_client is None:
        return False

    try:
        value = await redis_client.get(key)
        return value is not None
    except Exception as e:
        print(f"Redis exists check error for {key}: {e}")
        return False
