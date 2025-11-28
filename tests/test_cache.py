"""
Unit Tests for Redis Cache - Phase 2.1

Tests for:
- Cache key generation
- Cache invalidation strategies
- Cache metrics
"""

import pytest
import uuid
from backend.cache import (
    analysis_cache_key,
    resume_cache_key,
    job_desc_cache_key,
    user_cache_pattern,
    CacheMetrics,
)

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit


class TestCacheKeyGeneration:
    """Test cases for cache key generation functions."""

    def test_analysis_cache_key(self):
        """Test analysis cache key generation."""
        resume_id = str(uuid.uuid4())
        job_desc_id = str(uuid.uuid4())

        key = analysis_cache_key(resume_id, job_desc_id)

        assert key.startswith("analysis:")
        assert resume_id in key
        assert job_desc_id in key
        assert key == f"analysis:{resume_id}:{job_desc_id}"

    def test_resume_cache_key(self):
        """Test resume cache key generation."""
        resume_id = str(uuid.uuid4())

        key = resume_cache_key(resume_id)

        assert key.startswith("resume:")
        assert resume_id in key
        assert key == f"resume:{resume_id}"

    def test_job_desc_cache_key(self):
        """Test job description cache key generation."""
        job_desc_id = str(uuid.uuid4())

        key = job_desc_cache_key(job_desc_id)

        assert key.startswith("job_desc:")
        assert job_desc_id in key
        assert key == f"job_desc:{job_desc_id}"

    def test_user_cache_pattern(self):
        """Test user cache pattern generation."""
        user_id = str(uuid.uuid4())

        pattern = user_cache_pattern(user_id)

        assert user_id in pattern
        assert "*" in pattern
        assert pattern == f"*:{user_id}:*"

    def test_cache_key_uniqueness(self):
        """Test that different IDs generate different cache keys."""
        id1 = str(uuid.uuid4())
        id2 = str(uuid.uuid4())

        key1 = resume_cache_key(id1)
        key2 = resume_cache_key(id2)

        assert key1 != key2

    def test_analysis_cache_key_order_matters(self):
        """Test that analysis cache key order matters."""
        resume_id = str(uuid.uuid4())
        job_desc_id = str(uuid.uuid4())

        key1 = analysis_cache_key(resume_id, job_desc_id)
        key2 = analysis_cache_key(job_desc_id, resume_id)

        # Keys should be different (order matters)
        assert key1 != key2


class TestCacheMetrics:
    """Test cases for cache metrics tracking."""

    def test_cache_metrics_initialization(self):
        """Test CacheMetrics initializes with zero counts."""
        metrics = CacheMetrics()

        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.get_hit_rate() == 0.0

    @pytest.mark.asyncio
    async def test_cache_metrics_record_hit(self):
        """Test recording cache hits."""
        metrics = CacheMetrics()

        await metrics.record_hit()
        await metrics.record_hit()
        await metrics.record_hit()

        assert metrics.hits == 3
        assert metrics.misses == 0

    @pytest.mark.asyncio
    async def test_cache_metrics_record_miss(self):
        """Test recording cache misses."""
        metrics = CacheMetrics()

        await metrics.record_miss()
        await metrics.record_miss()

        assert metrics.hits == 0
        assert metrics.misses == 2

    @pytest.mark.asyncio
    async def test_cache_metrics_hit_rate_calculation(self):
        """Test cache hit rate calculation."""
        metrics = CacheMetrics()

        # 3 hits, 1 miss = 75% hit rate
        await metrics.record_hit()
        await metrics.record_hit()
        await metrics.record_hit()
        await metrics.record_miss()

        hit_rate = metrics.get_hit_rate()
        assert hit_rate == 0.75

    @pytest.mark.asyncio
    async def test_cache_metrics_hit_rate_all_misses(self):
        """Test cache hit rate with all misses."""
        metrics = CacheMetrics()

        await metrics.record_miss()
        await metrics.record_miss()

        hit_rate = metrics.get_hit_rate()
        assert hit_rate == 0.0

    @pytest.mark.asyncio
    async def test_cache_metrics_hit_rate_all_hits(self):
        """Test cache hit rate with all hits."""
        metrics = CacheMetrics()

        await metrics.record_hit()
        await metrics.record_hit()

        hit_rate = metrics.get_hit_rate()
        assert hit_rate == 1.0

    def test_cache_metrics_reset(self):
        """Test resetting cache metrics."""
        metrics = CacheMetrics()
        metrics.hits = 10
        metrics.misses = 5

        metrics.reset()

        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.get_hit_rate() == 0.0

    @pytest.mark.asyncio
    async def test_cache_metrics_complex_scenario(self):
        """Test cache metrics in a realistic scenario."""
        metrics = CacheMetrics()

        # Simulate 100 cache operations: 70 hits, 30 misses
        for _ in range(70):
            await metrics.record_hit()
        for _ in range(30):
            await metrics.record_miss()

        assert metrics.hits == 70
        assert metrics.misses == 30
        assert metrics.get_hit_rate() == 0.70


# ============================================================================
# Integration Tests (require Redis connection)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_connection():
    """Test Redis connection can be established (integration test)."""
    # This would require a running Redis instance
    # Placeholder for future implementation
    pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_set_and_get():
    """Test setting and getting cache values (integration test)."""
    # This would test actual Redis operations
    # Placeholder for future implementation
    pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """Test cache TTL expiration (integration test)."""
    # This would test that cached values expire after TTL
    # Placeholder for future implementation
    pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_invalidation():
    """Test cache invalidation strategies (integration test)."""
    # This would test invalidation functions
    # Placeholder for future implementation
    pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_pattern_deletion():
    """Test deleting cache keys by pattern (integration test)."""
    # This would test delete_pattern function
    # Placeholder for future implementation
    pass
