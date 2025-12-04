"""
Rate Limiting Middleware - Phase 4

FastAPI middleware for per-user rate limiting.
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import logging

from backend.auth.rate_limiter import UserRateLimiter
from backend.database.session import get_session

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce per-user rate limits.

    Applies rate limiting to authenticated users based on their roles.
    Unauthenticated requests are not rate limited (handled by global limits if needed).
    """

    def __init__(self, app, redis_url: str = "redis://localhost:6379"):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            redis_url: Redis connection URL
        """
        super().__init__(app)
        self.rate_limiter = UserRateLimiter(redis_url=redis_url)

    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request and apply rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Skip rate limiting for certain paths
        if self._should_skip(request.url.path):
            return await call_next(request)

        # Try to get authenticated user
        user = None
        try:
            # Get user from JWT token if present
            from backend.auth.security import verify_token

            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                payload = verify_token(token, expected_type="access")

                if payload:
                    # Get user from database
                    async for session in get_session():
                        from backend.repositories.user_repository import UserRepository

                        user_repo = UserRepository(session)
                        user = await user_repo.get_by_id(payload["sub"])
                        break
        except Exception as e:
            logger.debug(f"Could not extract user for rate limiting: {e}")

        # If no authenticated user, skip rate limiting
        if not user:
            return await call_next(request)

        # Check rate limit
        user_roles = [role.name for role in user.roles] if user.roles else ["user"]

        is_allowed, rate_info = await self.rate_limiter.check_rate_limit(
            user_id=str(user.id),
            user_roles=user_roles,
            endpoint=request.url.path,
        )

        if not is_allowed:
            # Rate limit exceeded
            logger.warning(
                f"Rate limit exceeded for user {user.email} ({rate_info['limit_type']})"
            )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit_type": rate_info["limit_type"],
                    "limit": rate_info["limit"],
                    "current": rate_info["current"],
                    "reset_in_seconds": rate_info["reset_in_seconds"],
                    "role": rate_info["role"],
                },
                headers={
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(rate_info["reset_in_seconds"]),
                    "Retry-After": str(rate_info["reset_in_seconds"]),
                },
            )

        # Add rate limit headers to response
        response = await call_next(request)

        if "limits" in rate_info:
            # Add rate limit info headers
            minute_limits = rate_info["limits"]["per_minute"]
            response.headers["X-RateLimit-Limit-Minute"] = str(minute_limits["limit"])
            response.headers["X-RateLimit-Remaining-Minute"] = str(
                minute_limits["remaining"]
            )

            day_limits = rate_info["limits"]["per_day"]
            response.headers["X-RateLimit-Limit-Day"] = str(day_limits["limit"])
            response.headers["X-RateLimit-Remaining-Day"] = str(
                day_limits["remaining"]
            )

            response.headers["X-RateLimit-Role"] = rate_info["role"]

        return response

    def _should_skip(self, path: str) -> bool:
        """
        Check if path should skip rate limiting.

        Args:
            path: Request path

        Returns:
            True if should skip rate limiting
        """
        # Skip rate limiting for these paths
        skip_paths = [
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics",
            "/auth/login",  # Don't rate limit login (handled separately)
            "/auth/register",  # Don't rate limit registration
        ]

        for skip_path in skip_paths:
            if path.startswith(skip_path):
                return True

        return False


# Dependency for checking rate limits in endpoints
async def check_user_rate_limit(
    request: Request,
    rate_limiter: UserRateLimiter,
    user_id: str,
    user_roles: list,
):
    """
    Dependency to check rate limits for specific endpoints.

    Args:
        request: FastAPI request
        rate_limiter: UserRateLimiter instance
        user_id: User UUID as string
        user_roles: List of user role names

    Raises:
        HTTPException: If rate limit exceeded
    """
    is_allowed, rate_info = await rate_limiter.check_rate_limit(
        user_id=user_id,
        user_roles=user_roles,
        endpoint=request.url.path,
    )

    if not is_allowed:
        logger.warning(
            f"Rate limit exceeded for user {user_id} ({rate_info['limit_type']})"
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit_type": rate_info["limit_type"],
                "limit": rate_info["limit"],
                "current": rate_info["current"],
                "reset_in_seconds": rate_info["reset_in_seconds"],
                "role": rate_info["role"],
            },
            headers={
                "X-RateLimit-Limit": str(rate_info["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(rate_info["reset_in_seconds"]),
                "Retry-After": str(rate_info["reset_in_seconds"]),
            },
        )
