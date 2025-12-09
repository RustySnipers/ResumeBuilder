"""
Export Cache - Phase 5 Production Hardening

Caching for export results to improve performance and reduce server load.
"""

import hashlib
import json
from typing import Optional
import logging

try:
    from redis import Redis
except ImportError:
    Redis = None

logger = logging.getLogger(__name__)


class ExportCache:
    """
    Cache for export results (PDF, DOCX, HTML).

    TTL: 15 minutes (900 seconds)
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize export cache.

        Args:
            redis_url: Redis connection URL
        """
        try:
            self.redis = Redis.from_url(redis_url, decode_responses=False)
            self.enabled = True
            self.ttl = 900  # 15 minutes
            logger.info("Export cache initialized with Redis")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Export caching disabled.")
            self.redis = None
            self.enabled = False

    def _generate_cache_key(
        self,
        resume_id: str,
        format: str,
        template: str,
        **kwargs
    ) -> str:
        """
        Generate cache key for export.

        Args:
            resume_id: Resume UUID
            format: Export format (pdf, docx, html)
            template: Template name
            **kwargs: Additional parameters that affect output

        Returns:
            Cache key string
        """
        # Create deterministic key from parameters
        key_data = {
            "resume_id": resume_id,
            "format": format,
            "template": template,
            **kwargs
        }

        # Sort keys for consistency
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()

        return f"export_cache:{format}:{resume_id}:{key_hash[:16]}"

    def get(
        self,
        resume_id: str,
        format: str,
        template: str,
        **kwargs
    ) -> Optional[bytes]:
        """
        Get cached export result.

        Args:
            resume_id: Resume UUID
            format: Export format
            template: Template name
            **kwargs: Additional parameters

        Returns:
            Cached bytes or None if not found
        """
        if not self.enabled:
            return None

        try:
            cache_key = self._generate_cache_key(resume_id, format, template, **kwargs)
            cached_data = self.redis.get(cache_key)

            if cached_data:
                logger.info(f"Cache HIT for {format} export of resume {resume_id}")
                return cached_data
            else:
                logger.debug(f"Cache MISS for {format} export of resume {resume_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to get from cache: {e}")
            return None

    def set(
        self,
        resume_id: str,
        format: str,
        template: str,
        data: bytes,
        **kwargs
    ) -> bool:
        """
        Cache export result.

        Args:
            resume_id: Resume UUID
            format: Export format
            template: Template name
            data: Export data (bytes)
            **kwargs: Additional parameters

        Returns:
            True if cached successfully
        """
        if not self.enabled:
            return False

        # Don't cache if data is too large (> 5MB)
        if len(data) > 5 * 1024 * 1024:
            logger.warning(f"Export too large to cache: {len(data)} bytes")
            return False

        try:
            cache_key = self._generate_cache_key(resume_id, format, template, **kwargs)
            self.redis.setex(cache_key, self.ttl, data)
            logger.info(f"Cached {format} export of resume {resume_id} ({len(data)} bytes)")
            return True

        except Exception as e:
            logger.error(f"Failed to cache export: {e}")
            return False

    def invalidate(self, resume_id: str) -> int:
        """
        Invalidate all cached exports for a resume.

        Args:
            resume_id: Resume UUID

        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        try:
            # Find all cache keys for this resume
            pattern = f"export_cache:*:{resume_id}:*"
            keys = list(self.redis.scan_iter(match=pattern))

            if keys:
                deleted = self.redis.delete(*keys)
                logger.info(f"Invalidated {deleted} cached exports for resume {resume_id}")
                return deleted
            return 0

        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
            return 0

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        if not self.enabled:
            return {
                "enabled": False,
                "total_keys": 0,
                "memory_used": 0
            }

        try:
            # Count export cache keys
            pattern = "export_cache:*"
            keys = list(self.redis.scan_iter(match=pattern, count=1000))

            # Get memory info
            info = self.redis.info("memory")
            memory_used = info.get("used_memory_human", "0")

            return {
                "enabled": True,
                "total_keys": len(keys),
                "memory_used": memory_used,
                "ttl_seconds": self.ttl
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                "enabled": True,
                "error": str(e)
            }

    def clear_all(self) -> int:
        """
        Clear all export cache entries (admin function).

        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        try:
            pattern = "export_cache:*"
            keys = list(self.redis.scan_iter(match=pattern))

            if keys:
                deleted = self.redis.delete(*keys)
                logger.info(f"Cleared {deleted} export cache entries")
                return deleted
            return 0

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0
