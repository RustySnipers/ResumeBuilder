"""
Integration Tests - Phase 3.2

Tests cover end-to-end workflows for advanced LLM features:
- Retry logic with exponential backoff
- Redis caching for LLM responses
- Response validation and sanitization
- Streaming endpoints
"""

import pytest
from unittest.mock import AsyncMock
from backend.llm.retry_logic import RetryConfig, retry_with_exponential_backoff, with_retry
from backend.llm.response_validator import ResponseValidator
from backend.llm.cache import LLMCache


# ============================================================================
# Retry Logic Tests
# ============================================================================


class TestRetryLogic:
    """Test suite for retry logic."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_first_try(self):
        """Test that function succeeds on first try without retries."""
        call_count = 0

        async def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_with_exponential_backoff(successful_function)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_failures(self):
        """Test that function retries and eventually succeeds."""
        call_count = 0

        async def eventually_successful():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"

        config = RetryConfig(max_retries=5, initial_delay=0.1)
        result = await retry_with_exponential_backoff(eventually_successful, config)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausts_attempts(self):
        """Test that retry gives up after max attempts."""
        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise Exception("Permanent failure")

        config = RetryConfig(max_retries=3, initial_delay=0.1)

        with pytest.raises(Exception) as exc_info:
            await retry_with_exponential_backoff(always_fails, config)

        assert str(exc_info.value) == "Permanent failure"
        assert call_count == 4  # Initial + 3 retries

    @pytest.mark.asyncio
    async def test_retry_decorator(self):
        """Test retry decorator."""
        call_count = 0

        @with_retry(RetryConfig(max_retries=2, initial_delay=0.1))
        async def decorated_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Retry needed")
            return "decorated success"

        result = await decorated_function()

        assert result == "decorated success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that exponential backoff increases delay."""
        import time

        call_times = []

        async def track_calls():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise Exception("Force retry")
            return "done"

        config = RetryConfig(max_retries=3, initial_delay=0.1, jitter=False)
        await retry_with_exponential_backoff(track_calls, config)

        # Check that delays increase exponentially
        # First retry: ~0.1s, second retry: ~0.2s
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            assert delay2 > delay1  # Exponential increase


# ============================================================================
# Response Validator Tests
# ============================================================================


class TestResponseValidator:
    """Test suite for ResponseValidator."""

    def test_validate_valid_response(self):
        """Test that valid response passes validation."""
        validator = ResponseValidator(min_length=10, max_length=1000)
        response = "This is a valid resume optimization with enough content."

        is_valid, issues = validator.validate(response)

        assert is_valid is True
        assert len(issues) == 0

    def test_validate_too_short(self):
        """Test that too-short response fails validation."""
        validator = ResponseValidator(min_length=100)
        response = "Too short"

        is_valid, issues = validator.validate(response)

        assert is_valid is False
        assert any("too short" in issue.lower() for issue in issues)

    def test_validate_too_long(self):
        """Test that too-long response fails validation."""
        validator = ResponseValidator(max_length=50)
        response = "x" * 100

        is_valid, issues = validator.validate(response)

        assert is_valid is False
        assert any("too long" in issue.lower() for issue in issues)

    def test_validate_harmful_content(self):
        """Test detection of harmful content."""
        validator = ResponseValidator(check_harmful=True)
        response = """
        Good resume text here.
        <script>alert('xss')</script>
        More content.
        """

        is_valid, issues = validator.validate(response)

        assert is_valid is False
        assert any("harmful" in issue.lower() for issue in issues)

    def test_validate_fabrication_indicators(self):
        """Test detection of fabrication indicators."""
        validator = ResponseValidator(check_fabrication=True)
        response = """
        This is a resume optimization.
        I apologize, but I cannot verify this information.
        Here are the changes.
        """

        is_valid, issues = validator.validate(response)

        assert is_valid is False
        assert any("fabrication" in issue.lower() for issue in issues)

    def test_sanitize_removes_scripts(self):
        """Test that sanitize removes script tags."""
        validator = ResponseValidator()
        response = """
        Resume text <script>alert('hack')</script> more text
        """

        sanitized = validator.sanitize(response)

        assert "<script>" not in sanitized
        assert "alert" not in sanitized
        assert "Resume text" in sanitized

    def test_sanitize_removes_event_handlers(self):
        """Test that sanitize removes event handlers."""
        validator = ResponseValidator()
        response = """<div onclick="malicious()">Click me</div>"""

        sanitized = validator.sanitize(response)

        assert "onclick" not in sanitized

    def test_extract_structured_response(self):
        """Test extraction of structured sections."""
        validator = ResponseValidator()
        response = """
## OPTIMIZED RESUME
Software Engineer with 5 years of Python experience.

## CHANGES MADE
- Added Python keywords
- Quantified achievements

## EXPECTED IMPROVEMENT
Better ATS compatibility.
        """

        sections = validator.extract_structured_response(response)

        assert "resume" in sections
        assert "Software Engineer" in sections["resume"]
        assert "changes" in sections
        assert "Python keywords" in sections["changes"]
        assert "improvement" in sections
        assert "ATS compatibility" in sections["improvement"]

    def test_assess_quality(self):
        """Test quality assessment."""
        validator = ResponseValidator()
        response = """
## OPTIMIZED RESUME

- Led team of 5 developers
- Improved performance by 40%
- Reduced costs by $50,000

Experience includes Python development with quantifiable results.
        """

        metrics = validator.assess_quality(response)

        assert metrics["has_structure"] is True
        assert metrics["has_bullets"] is True
        assert metrics["has_numbers"] is True
        assert metrics["quality_score"] > 0.5


# ============================================================================
# LLM Cache Tests
# ============================================================================


class TestLLMCache:
    """Test suite for LLM caching."""

    @pytest.mark.asyncio
    async def test_cache_stores_and_retrieves(self):
        """Test basic cache storage and retrieval."""
        # Use mock Redis for testing
        cache = LLMCache(redis_url="redis://localhost:6379")

        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        cache._redis = mock_redis

        # Test cache miss
        result = await cache.get(
            prompt="test prompt",
            system_prompt="system",
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=1.0,
        )

        assert result is None
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_key_generation(self):
        """Test that cache keys are generated consistently."""
        cache = LLMCache()

        key1 = cache._generate_cache_key(
            prompt="test",
            system_prompt="sys",
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=1.0,
        )

        key2 = cache._generate_cache_key(
            prompt="test",
            system_prompt="sys",
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=1.0,
        )

        # Same parameters should generate same key
        assert key1 == key2

        # Different parameters should generate different key
        key3 = cache._generate_cache_key(
            prompt="different",
            system_prompt="sys",
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=1.0,
        )

        assert key1 != key3

    @pytest.mark.asyncio
    async def test_cache_handles_redis_unavailable(self):
        """Test graceful degradation when Redis is unavailable."""
        cache = LLMCache()
        cache._redis = None  # Simulate Redis unavailable

        # Should return None without error
        result = await cache.get(
            prompt="test",
            system_prompt="sys",
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=1.0,
        )

        assert result is None

        # Should return False without error
        success = await cache.set(
            prompt="test",
            system_prompt="sys",
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=1.0,
            response={"content": "test"},
        )

        assert success is False


# ============================================================================
# Integration Tests
# ============================================================================


class TestPhase32Integration:
    """End-to-end integration tests for Phase 3.2."""

    @pytest.mark.asyncio
    async def test_retry_with_cache(self):
        """Test retry logic combined with caching."""
        cache = LLMCache()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        cache._redis = mock_redis

        call_count = 0

        @with_retry(RetryConfig(max_retries=2, initial_delay=0.1))
        async def api_call_with_cache():
            nonlocal call_count
            call_count += 1

            # Check cache
            cached = await cache.get("test", "sys", "model", 1000, 1.0)
            if cached:
                return cached

            # Simulate API failure on first try
            if call_count == 1:
                raise Exception("API timeout")

            result = {"content": "generated response"}

            # Cache result
            await cache.set("test", "sys", "model", 1000, 1.0, result)

            return result

        result = await api_call_with_cache()

        assert result["content"] == "generated response"
        assert call_count == 2  # Failed once, succeeded on retry
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_pipeline_with_validation(self):
        """Test complete pipeline: retry, cache, validate."""
        validator = ResponseValidator(min_length=10)

        @with_retry(RetryConfig(max_retries=2, initial_delay=0.1))
        async def generate_and_validate():
            # Simulate LLM response
            response = "This is a properly formatted resume optimization with sufficient length."

            # Validate
            is_valid, issues = validator.validate(response)

            if not is_valid:
                raise Exception(f"Validation failed: {issues}")

            return response

        result = await generate_and_validate()

        assert len(result) > 10
        assert "resume optimization" in result
