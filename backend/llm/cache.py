"""
LLM Response Cache - Phase 3.2

Redis-based caching for LLM responses to reduce costs and latency.
"""

import hashlib
import json
import logging
from typing import Optional, Dict, Any
import redis.asyncio as aioredis
from datetime import timedelta

logger = logging.getLogger(__name__)


class LLMCache:
    """
    Redis-based cache for LLM responses.

    Caches responses by prompt hash to avoid duplicate API calls
    for identical requests.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        ttl_seconds: int = 3600,
        key_prefix: str = "llm:",
    ):
        """
        Initialize LLM cache.

        Args:
            redis_url: Redis connection URL
            ttl_seconds: Time-to-live for cached responses (default: 1 hour)
            key_prefix: Prefix for cache keys
        """
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._redis is None:
            try:
                self._redis = await aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                logger.info("Connected to Redis for LLM caching")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
                self._redis = None

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Disconnected from Redis")

    def _generate_cache_key(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """
        Generate cache key from request parameters.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            model: Model name
            max_tokens: Max tokens
            temperature: Temperature

        Returns:
            Cache key hash
        """
        # Create a unique identifier from all parameters
        cache_data = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Generate hash
        cache_str = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.sha256(cache_str.encode()).hexdigest()

        return f"{self.key_prefix}{cache_hash}"

    async def get(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response if available.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            model: Model name
            max_tokens: Max tokens
            temperature: Temperature

        Returns:
            Cached response dict or None if not found
        """
        if not self._redis:
            return None

        try:
            cache_key = self._generate_cache_key(
                prompt, system_prompt, model, max_tokens, temperature
            )

            cached_data = await self._redis.get(cache_key)

            if cached_data:
                logger.info(f"Cache HIT for key: {cache_key[:16]}...")
                return json.loads(cached_data)

            logger.debug(f"Cache MISS for key: {cache_key[:16]}...")
            return None

        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None

    async def set(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        response: Dict[str, Any],
    ) -> bool:
        """
        Cache LLM response.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            model: Model name
            max_tokens: Max tokens
            temperature: Temperature
            response: Response dict to cache

        Returns:
            True if successfully cached, False otherwise
        """
        if not self._redis:
            return False

        try:
            cache_key = self._generate_cache_key(
                prompt, system_prompt, model, max_tokens, temperature
            )

            await self._redis.setex(
                cache_key,
                timedelta(seconds=self.ttl_seconds),
                json.dumps(response)
            )

            logger.info(f"Cached response for key: {cache_key[:16]}...")
            return True

        except Exception as e:
            logger.error(f"Error caching response: {e}")
            return False

    async def invalidate(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> bool:
        """
        Invalidate cached response.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            model: Model name
            max_tokens: Max tokens
            temperature: Temperature

        Returns:
            True if successfully invalidated, False otherwise
        """
        if not self._redis:
            return False

        try:
            cache_key = self._generate_cache_key(
                prompt, system_prompt, model, max_tokens, temperature
            )

            await self._redis.delete(cache_key)
            logger.info(f"Invalidated cache for key: {cache_key[:16]}...")
            return True

        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return False

    async def clear_all(self) -> bool:
        """
        Clear all cached LLM responses.

        Returns:
            True if successful, False otherwise
        """
        if not self._redis:
            return False

        try:
            # Find all keys with our prefix
            cursor = 0
            pattern = f"{self.key_prefix}*"
            deleted_count = 0

            while True:
                cursor, keys = await self._redis.scan(
                    cursor, match=pattern, count=100
                )

                if keys:
                    await self._redis.delete(*keys)
                    deleted_count += len(keys)

                if cursor == 0:
                    break

            logger.info(f"Cleared {deleted_count} cached responses")
            return True

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    async def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self._redis:
            return {"total_keys": 0}

        try:
            # Count keys with our prefix
            cursor = 0
            pattern = f"{self.key_prefix}*"
            total_keys = 0

            while True:
                cursor, keys = await self._redis.scan(
                    cursor, match=pattern, count=100
                )
                total_keys += len(keys)

                if cursor == 0:
                    break

            return {
                "total_keys": total_keys,
                "ttl_seconds": self.ttl_seconds,
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"total_keys": 0}
