"""
Export Rate Limiter - Phase 5 Production Hardening

Rate limiting specifically for export endpoints to prevent abuse.
"""

import time
from typing import Optional
from redis import Redis
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)


class ExportRateLimiter:
    """
    Rate limiter for export endpoints.

    Limits:
    - 10 exports per minute per user
    - 50 exports per day per user
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize export rate limiter.

        Args:
            redis_url: Redis connection URL
        """
        try:
            self.redis = Redis.from_url(redis_url, decode_responses=True)
            self.enabled = True
            logger.info("Export rate limiter initialized with Redis")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Rate limiting disabled.")
            self.redis = None
            self.enabled = False

    def check_rate_limit(self, user_id: str, operation: str = "export") -> dict:
        """
        Check if user has exceeded rate limits.

        Args:
            user_id: User UUID
            operation: Operation type (export, pdf, docx, preview)

        Returns:
            Dict with rate limit info

        Raises:
            HTTPException: If rate limit exceeded
        """
        if not self.enabled:
            return {
                "allowed": True,
                "remaining_minute": -1,
                "remaining_day": -1
            }

        current_time = int(time.time())
        minute_key = f"export_rate:{user_id}:{operation}:minute:{current_time // 60}"
        day_key = f"export_rate:{user_id}:{operation}:day:{current_time // 86400}"

        # Limits
        MINUTE_LIMIT = 10
        DAY_LIMIT = 50

        try:
            # Get current counts
            minute_count = self.redis.get(minute_key)
            day_count = self.redis.get(day_key)

            minute_count = int(minute_count) if minute_count else 0
            day_count = int(day_count) if day_count else 0

            # Check limits
            if minute_count >= MINUTE_LIMIT:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Export rate limit exceeded: {MINUTE_LIMIT} exports per minute. Please try again later.",
                    headers={
                        "Retry-After": "60",
                        "X-RateLimit-Limit-Minute": str(MINUTE_LIMIT),
                        "X-RateLimit-Remaining-Minute": "0",
                    }
                )

            if day_count >= DAY_LIMIT:
                seconds_until_reset = 86400 - (current_time % 86400)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Daily export limit exceeded: {DAY_LIMIT} exports per day. Resets in {seconds_until_reset // 3600} hours.",
                    headers={
                        "Retry-After": str(seconds_until_reset),
                        "X-RateLimit-Limit-Day": str(DAY_LIMIT),
                        "X-RateLimit-Remaining-Day": "0",
                    }
                )

            # Increment counters
            pipe = self.redis.pipeline()
            pipe.incr(minute_key)
            pipe.expire(minute_key, 120)  # 2 minutes TTL
            pipe.incr(day_key)
            pipe.expire(day_key, 86400 * 2)  # 2 days TTL
            pipe.execute()

            return {
                "allowed": True,
                "remaining_minute": MINUTE_LIMIT - minute_count - 1,
                "remaining_day": DAY_LIMIT - day_count - 1,
                "limit_minute": MINUTE_LIMIT,
                "limit_day": DAY_LIMIT
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Allow request if Redis fails
            return {
                "allowed": True,
                "remaining_minute": -1,
                "remaining_day": -1
            }

    def get_rate_limit_status(self, user_id: str, operation: str = "export") -> dict:
        """
        Get current rate limit status for user.

        Args:
            user_id: User UUID
            operation: Operation type

        Returns:
            Dict with current limits and remaining quota
        """
        if not self.enabled:
            return {
                "limit_minute": -1,
                "remaining_minute": -1,
                "limit_day": -1,
                "remaining_day": -1,
                "enabled": False
            }

        current_time = int(time.time())
        minute_key = f"export_rate:{user_id}:{operation}:minute:{current_time // 60}"
        day_key = f"export_rate:{user_id}:{operation}:day:{current_time // 86400}"

        MINUTE_LIMIT = 10
        DAY_LIMIT = 50

        try:
            minute_count = self.redis.get(minute_key)
            day_count = self.redis.get(day_key)

            minute_count = int(minute_count) if minute_count else 0
            day_count = int(day_count) if day_count else 0

            return {
                "limit_minute": MINUTE_LIMIT,
                "remaining_minute": max(0, MINUTE_LIMIT - minute_count),
                "limit_day": DAY_LIMIT,
                "remaining_day": max(0, DAY_LIMIT - day_count),
                "enabled": True
            }
        except Exception as e:
            logger.error(f"Failed to get rate limit status: {e}")
            return {
                "limit_minute": MINUTE_LIMIT,
                "remaining_minute": -1,
                "limit_day": DAY_LIMIT,
                "remaining_day": -1,
                "enabled": False,
                "error": str(e)
            }

    def reset_user_limits(self, user_id: str, operation: str = "export") -> bool:
        """
        Reset rate limits for a user (admin function).

        Args:
            user_id: User UUID
            operation: Operation type

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        try:
            current_time = int(time.time())
            minute_key = f"export_rate:{user_id}:{operation}:minute:{current_time // 60}"
            day_key = f"export_rate:{user_id}:{operation}:day:{current_time // 86400}"

            self.redis.delete(minute_key, day_key)
            logger.info(f"Reset rate limits for user {user_id}, operation {operation}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset rate limits: {e}")
            return False
