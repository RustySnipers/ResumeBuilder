"""
Redis Cache Configuration - Phase 2.1

This module provides Redis connection pooling and caching utilities for the Resume Builder application.

Features:
- Connection pooling with configurable pool size
- TTL-based caching policies
- Cache invalidation strategies
- JSON serialization for complex objects
"""

import redis.asyncio as aioredis
import json
import os
from typing import Optional, Any


# ============================================================================
# Redis Configuration
# ============================================================================

# Redis URL from environment variable with fallback to local development
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Default TTL values (in seconds)
DEFAULT_TTL = 3600  # 1 hour
ANALYSIS_TTL = 3600  # 1 hour for analysis results
RESUME_TTL = 1800  # 30 minutes for resume data
JOB_DESC_TTL = 1800  # 30 minutes for job descriptions

# Create Redis connection pool
# decode_responses=False to handle binary data properly
# max_connections: Maximum number of connections in the pool
redis_pool = aioredis.ConnectionPool.from_url(
    REDIS_URL,
    max_connections=10,
    decode_responses=False,
)

# Redis client instance
redis_client: Optional[aioredis.Redis] = None


# ============================================================================
# Connection Management
# ============================================================================

async def init_redis() -> None:
    """
    Initialize Redis connection pool.

    Call this during application startup to establish Redis connections.
    """
    global redis_client
    redis_client = aioredis.Redis(connection_pool=redis_pool)


async def close_redis() -> None:
    """
    Close Redis connection pool.

    Call this during application shutdown to ensure clean connection closure.
    """
    if redis_client:
        await redis_client.close()
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
        # Serialize to JSON
        serialized = json.dumps(value)

        # Set with TTL
        ttl_seconds = ttl or DEFAULT_TTL
        await redis_client.setex(key, ttl_seconds, serialized)
        return True
    except Exception as e:
        # Log error in production
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
        # Log error in production
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
        # Log error in production
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
        return await redis_client.exists(key) > 0
    except Exception:
        return False


# ============================================================================
# Cache Key Generators
# ============================================================================

def analysis_cache_key(resume_id: str, job_desc_id: str) -> str:
    """
    Generate cache key for analysis results.

    Args:
        resume_id: Resume UUID
        job_desc_id: Job description UUID

    Returns:
        Cache key string
    """
    return f"analysis:{resume_id}:{job_desc_id}"


def resume_cache_key(resume_id: str) -> str:
    """
    Generate cache key for resume data.

    Args:
        resume_id: Resume UUID

    Returns:
        Cache key string
    """
    return f"resume:{resume_id}"


def job_desc_cache_key(job_desc_id: str) -> str:
    """
    Generate cache key for job description data.

    Args:
        job_desc_id: Job description UUID

    Returns:
        Cache key string
    """
    return f"job_desc:{job_desc_id}"


def user_cache_pattern(user_id: str) -> str:
    """
    Generate cache key pattern for all user data.

    Args:
        user_id: User UUID

    Returns:
        Cache key pattern (for use with delete_pattern)
    """
    return f"*:{user_id}:*"


# ============================================================================
# Cache Invalidation Strategies
# ============================================================================

async def invalidate_resume_cache(resume_id: str) -> None:
    """
    Invalidate cache for a specific resume and all related analyses.

    Args:
        resume_id: Resume UUID
    """
    # Delete resume cache
    await delete_cache(resume_cache_key(resume_id))

    # Delete all analyses for this resume
    await delete_pattern(f"analysis:{resume_id}:*")


async def invalidate_job_desc_cache(job_desc_id: str) -> None:
    """
    Invalidate cache for a specific job description and all related analyses.

    Args:
        job_desc_id: Job description UUID
    """
    # Delete job description cache
    await delete_cache(job_desc_cache_key(job_desc_id))

    # Delete all analyses for this job description
    await delete_pattern(f"analysis:*:{job_desc_id}")


async def invalidate_user_cache(user_id: str) -> None:
    """
    Invalidate all cache for a specific user.

    Args:
        user_id: User UUID
    """
    await delete_pattern(user_cache_pattern(user_id))


# ============================================================================
# Metrics Tracking
# ============================================================================

class CacheMetrics:
    """
    Track cache hit/miss metrics for monitoring.

    In production, these would be sent to Prometheus or CloudWatch.
    """

    def __init__(self):
        self.hits = 0
        self.misses = 0

    async def record_hit(self) -> None:
        """Record a cache hit."""
        self.hits += 1

    async def record_miss(self) -> None:
        """Record a cache miss."""
        self.misses += 1

    def get_hit_rate(self) -> float:
        """
        Calculate cache hit rate.

        Returns:
            float: Hit rate (0.0 to 1.0)
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def reset(self) -> None:
        """Reset metrics counters."""
        self.hits = 0
        self.misses = 0


# Global metrics instance
cache_metrics = CacheMetrics()
