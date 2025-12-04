"""
Per-User Rate Limiting - Phase 4

Redis-based rate limiting with role-based quotas.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)


class UserRateLimiter:
    """
    Rate limiter with per-user quotas based on role.

    Uses Redis for distributed rate limiting with sliding window algorithm.
    """

    # Rate limits by role (requests per minute, requests per day)
    RATE_LIMITS = {
        "user": {
            "requests_per_minute": 10,
            "requests_per_day": 100,
        },
        "premium": {
            "requests_per_minute": 50,
            "requests_per_day": 1000,
        },
        "admin": {
            "requests_per_minute": 100,
            "requests_per_day": 10000,
        },
    }

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize rate limiter with Redis connection.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self):
        """Establish Redis connection."""
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                self.redis_url, decode_responses=True
            )
            logger.info("Rate limiter connected to Redis")

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Rate limiter disconnected from Redis")

    def _get_user_role(self, user_roles: list) -> str:
        """
        Get highest priority role for rate limiting.

        Priority: admin > premium > user

        Args:
            user_roles: List of role names

        Returns:
            Role name for rate limiting
        """
        if "admin" in user_roles:
            return "admin"
        elif "premium" in user_roles:
            return "premium"
        else:
            return "user"

    def _get_rate_limits(self, role: str) -> Dict[str, int]:
        """
        Get rate limits for a role.

        Args:
            role: Role name

        Returns:
            Dict with rate limits
        """
        return self.RATE_LIMITS.get(role, self.RATE_LIMITS["user"])

    async def check_rate_limit(
        self,
        user_id: str,
        user_roles: list,
        endpoint: str = "general",
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if user has exceeded rate limit.

        Uses sliding window algorithm for both minute and day windows.

        Args:
            user_id: User UUID as string
            user_roles: List of user role names
            endpoint: Optional endpoint identifier

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        if not self.redis_client:
            await self.connect()

        # Get user's role and limits
        role = self._get_user_role(user_roles)
        limits = self._get_rate_limits(role)

        # Check minute window
        minute_key = f"ratelimit:user:{user_id}:minute"
        minute_count = await self._get_request_count(minute_key, window_seconds=60)

        if minute_count >= limits["requests_per_minute"]:
            return False, {
                "allowed": False,
                "limit_type": "per_minute",
                "limit": limits["requests_per_minute"],
                "current": minute_count,
                "reset_in_seconds": await self._get_ttl(minute_key),
                "role": role,
            }

        # Check day window
        day_key = f"ratelimit:user:{user_id}:day"
        day_count = await self._get_request_count(day_key, window_seconds=86400)

        if day_count >= limits["requests_per_day"]:
            return False, {
                "allowed": False,
                "limit_type": "per_day",
                "limit": limits["requests_per_day"],
                "current": day_count,
                "reset_in_seconds": await self._get_ttl(day_key),
                "role": role,
            }

        # Increment counters
        await self._increment_request_count(minute_key, ttl_seconds=60)
        await self._increment_request_count(day_key, ttl_seconds=86400)

        return True, {
            "allowed": True,
            "limits": {
                "per_minute": {
                    "limit": limits["requests_per_minute"],
                    "remaining": limits["requests_per_minute"] - minute_count - 1,
                },
                "per_day": {
                    "limit": limits["requests_per_day"],
                    "remaining": limits["requests_per_day"] - day_count - 1,
                },
            },
            "role": role,
        }

    async def _get_request_count(self, key: str, window_seconds: int) -> int:
        """
        Get request count for a time window using sorted set.

        Args:
            key: Redis key
            window_seconds: Time window in seconds

        Returns:
            Number of requests in window
        """
        now = datetime.utcnow().timestamp()
        window_start = now - window_seconds

        # Remove old entries
        await self.redis_client.zremrangebyscore(key, 0, window_start)

        # Count entries in window
        count = await self.redis_client.zcount(key, window_start, now)

        return count

    async def _increment_request_count(self, key: str, ttl_seconds: int):
        """
        Increment request count using sorted set.

        Args:
            key: Redis key
            ttl_seconds: TTL for the key
        """
        now = datetime.utcnow().timestamp()

        # Add current timestamp to sorted set
        await self.redis_client.zadd(key, {str(now): now})

        # Set expiry
        await self.redis_client.expire(key, ttl_seconds)

    async def _get_ttl(self, key: str) -> int:
        """
        Get TTL for a key.

        Args:
            key: Redis key

        Returns:
            TTL in seconds
        """
        ttl = await self.redis_client.ttl(key)
        return max(ttl, 0)

    async def get_user_stats(
        self, user_id: str, user_roles: list
    ) -> Dict[str, Any]:
        """
        Get current rate limit stats for a user.

        Args:
            user_id: User UUID as string
            user_roles: List of user role names

        Returns:
            Dict with rate limit statistics
        """
        if not self.redis_client:
            await self.connect()

        role = self._get_user_role(user_roles)
        limits = self._get_rate_limits(role)

        minute_key = f"ratelimit:user:{user_id}:minute"
        day_key = f"ratelimit:user:{user_id}:day"

        minute_count = await self._get_request_count(minute_key, window_seconds=60)
        day_count = await self._get_request_count(day_key, window_seconds=86400)

        return {
            "role": role,
            "per_minute": {
                "limit": limits["requests_per_minute"],
                "used": minute_count,
                "remaining": max(0, limits["requests_per_minute"] - minute_count),
                "reset_in_seconds": await self._get_ttl(minute_key),
            },
            "per_day": {
                "limit": limits["requests_per_day"],
                "used": day_count,
                "remaining": max(0, limits["requests_per_day"] - day_count),
                "reset_in_seconds": await self._get_ttl(day_key),
            },
        }

    async def reset_user_limits(self, user_id: str):
        """
        Reset rate limits for a user (admin operation).

        Args:
            user_id: User UUID as string
        """
        if not self.redis_client:
            await self.connect()

        minute_key = f"ratelimit:user:{user_id}:minute"
        day_key = f"ratelimit:user:{user_id}:day"

        await self.redis_client.delete(minute_key)
        await self.redis_client.delete(day_key)

        logger.info(f"Rate limits reset for user {user_id}")

    async def cleanup_expired(self):
        """
        Cleanup expired rate limit keys.

        This is handled automatically by Redis TTL, but can be called
        for manual cleanup.
        """
        if not self.redis_client:
            await self.connect()

        # Scan for ratelimit keys
        cursor = 0
        deleted_count = 0

        while True:
            cursor, keys = await self.redis_client.scan(
                cursor, match="ratelimit:*", count=100
            )

            for key in keys:
                ttl = await self.redis_client.ttl(key)
                if ttl == -1:  # No expiry set
                    await self.redis_client.delete(key)
                    deleted_count += 1

            if cursor == 0:
                break

        logger.info(f"Cleaned up {deleted_count} expired rate limit keys")
        return deleted_count
