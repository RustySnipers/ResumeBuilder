"""Analytics Tracking Middleware

Automatically tracks API requests for analytics.
"""
import time
from typing import Callable, Optional
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.database import get_session
from backend.models.user_activity import ActivityType


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Middleware to track API requests for analytics

    Automatically records:
    - API request activity
    - Response times
    - Status codes
    - Endpoint usage
    - User associations
    """

    # Endpoints to exclude from tracking (health checks, metrics, etc.)
    EXCLUDED_PATHS = {
        "/",
        "/health",
        "/health/ready",
        "/health/live",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track analytics

        Args:
            request: FastAPI request
            call_next: Next middleware in chain

        Returns:
            Response
        """
        # Skip tracking for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Record start time
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        # Track activity asynchronously (don't block response)
        try:
            await self._track_request(
                request=request,
                response=response,
                response_time_ms=response_time_ms,
            )
        except Exception as e:
            # Log error but don't fail the request
            print(f"Analytics tracking error: {e}")

        return response

    async def _track_request(
        self,
        request: Request,
        response: Response,
        response_time_ms: int,
    ) -> None:
        """Track request analytics

        Args:
            request: FastAPI request
            response: FastAPI response
            response_time_ms: Response time in milliseconds
        """
        # Get user ID from request state if authenticated
        user_id: Optional[UUID] = None
        if hasattr(request.state, "user"):
            user_id = request.state.user.id

        # Get IP address
        ip_address = None
        if request.client:
            ip_address = request.client.host

        # Get user agent
        user_agent = request.headers.get("user-agent")

        # Determine activity type based on endpoint
        activity_type = self._get_activity_type(request.url.path, request.method)

        # Skip if no specific activity type
        if not activity_type:
            activity_type = ActivityType.API_REQUEST

        # Create activity record
        async for session in get_session():
            try:
                from backend.repositories.user_activity_repository import UserActivityRepository

                activity_repo = UserActivityRepository(session)

                await activity_repo.create_activity(
                    activity_type=activity_type,
                    user_id=user_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=response.status_code,
                    response_time_ms=response_time_ms,
                )

                await session.commit()
            except Exception as e:
                print(f"Failed to track activity: {e}")
                await session.rollback()
            finally:
                await session.close()
            break

    def _get_activity_type(self, path: str, method: str) -> Optional[ActivityType]:
        """Determine activity type from endpoint

        Args:
            path: Request path
            method: HTTP method

        Returns:
            ActivityType or None
        """
        # Authentication endpoints
        if path == "/auth/login" and method == "POST":
            return ActivityType.LOGIN
        if path == "/auth/logout" and method == "POST":
            return ActivityType.LOGOUT
        if path == "/auth/register" and method == "POST":
            return ActivityType.REGISTER
        if path == "/auth/change-password" and method == "POST":
            return ActivityType.PASSWORD_CHANGE
        if path == "/auth/reset-password" and method == "POST":
            return ActivityType.PASSWORD_RESET
        if path == "/auth/verify-email" and method == "POST":
            return ActivityType.EMAIL_VERIFIED

        # Resume operations
        if "/resumes" in path:
            if method == "POST":
                return ActivityType.RESUME_CREATED
            if method in ("PUT", "PATCH"):
                return ActivityType.RESUME_UPDATED
            if method == "DELETE":
                return ActivityType.RESUME_DELETED

        # Job description operations
        if "/job-descriptions" in path:
            if method == "POST":
                return ActivityType.JOB_DESCRIPTION_CREATED
            if method in ("PUT", "PATCH"):
                return ActivityType.JOB_DESCRIPTION_UPDATED
            if method == "DELETE":
                return ActivityType.JOB_DESCRIPTION_DELETED

        # Analysis operations
        if "/analyze" in path and method == "POST":
            return ActivityType.RESUME_ANALYZED

        # Generation operations
        if "/generate" in path:
            if "/stream" in path:
                return ActivityType.GENERATION_STREAM_STARTED
            return ActivityType.GENERATION_STARTED

        # Export operations
        if "/export" in path and method == "POST":
            if "/pdf" in path:
                return ActivityType.EXPORT_PDF
            if "/docx" in path:
                return ActivityType.EXPORT_DOCX
            if "/preview" in path or "/html" in path:
                return ActivityType.EXPORT_HTML

        # API key operations
        if "/api-keys" in path:
            if method == "POST":
                return ActivityType.API_KEY_CREATED
            if method == "DELETE":
                return ActivityType.API_KEY_REVOKED

        # Default to API request
        return ActivityType.API_REQUEST
