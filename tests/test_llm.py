"""
Comprehensive LLM Tests - Phase 3.1

Tests cover:
- ClaudeClient async operations
- Streaming functionality
- Rate limiting
- Cost tracking
- Prompt template generation
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from backend.llm.claude_client import ClaudeClient, RateLimiter
from backend.llm.cost_tracker import CostTracker, RequestRecord
from backend.llm.prompts import PromptTemplates
from datetime import datetime


# ============================================================================
# RateLimiter Tests
# ============================================================================


class TestRateLimiter:
    """Test suite for RateLimiter."""

    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly."""
        limiter = RateLimiter(max_requests_per_minute=60)
        assert limiter.max_requests == 60
        assert limiter.tokens == 60

    @pytest.mark.asyncio
    async def test_rate_limiter_acquire(self):
        """Test acquiring tokens from rate limiter."""
        limiter = RateLimiter(max_requests_per_minute=60)
        initial_tokens = limiter.tokens

        await limiter.acquire()
        assert limiter.tokens == initial_tokens - 1

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_when_exhausted(self):
        """Test that rate limiter blocks when tokens are exhausted."""
        limiter = RateLimiter(max_requests_per_minute=2)

        # Exhaust tokens
        await limiter.acquire()
        await limiter.acquire()

        # This should block briefly
        start = datetime.utcnow()
        await limiter.acquire()
        duration = (datetime.utcnow() - start).total_seconds()

        # Should have waited for token refill
        assert duration > 0.05  # At least 50ms wait

    @pytest.mark.asyncio
    async def test_rate_limiter_refills_tokens(self):
        """Test that tokens refill over time."""
        limiter = RateLimiter(max_requests_per_minute=60)

        # Exhaust some tokens
        await limiter.acquire()
        await limiter.acquire()

        # Wait for refill
        await asyncio.sleep(2)
        await limiter._refill_tokens()

        # Tokens should be refilled
        assert limiter.tokens > 58  # Should be close to max


# ============================================================================
# CostTracker Tests
# ============================================================================


class TestCostTracker:
    """Test suite for CostTracker."""

    def test_cost_tracker_initialization(self):
        """Test cost tracker initializes correctly."""
        tracker = CostTracker()
        assert tracker.total_input_tokens == 0
        assert tracker.total_output_tokens == 0
        assert tracker.total_cost == 0.0
        assert len(tracker.requests) == 0

    def test_track_request(self):
        """Test tracking a single request."""
        tracker = CostTracker()
        tracker.track_request(
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
            cost=0.0105,
        )

        assert tracker.total_input_tokens == 1000
        assert tracker.total_output_tokens == 500
        assert tracker.total_cost == 0.0105
        assert len(tracker.requests) == 1

    def test_track_multiple_requests(self):
        """Test tracking multiple requests."""
        tracker = CostTracker()

        for i in range(5):
            tracker.track_request(
                model="claude-sonnet-4-20250514",
                input_tokens=1000,
                output_tokens=500,
                cost=0.01,
            )

        assert tracker.total_input_tokens == 5000
        assert tracker.total_output_tokens == 2500
        assert tracker.total_cost == 0.05
        assert len(tracker.requests) == 5

    def test_get_stats(self):
        """Test getting usage statistics."""
        tracker = CostTracker()
        tracker.track_request(
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
            cost=0.01,
        )

        stats = tracker.get_stats()
        assert stats["total_requests"] == 1
        assert stats["total_input_tokens"] == 1000
        assert stats["total_output_tokens"] == 500
        assert stats["total_tokens"] == 1500
        assert stats["total_cost"] == 0.01
        assert stats["average_cost_per_request"] == 0.01

    def test_track_by_model(self):
        """Test per-model statistics."""
        tracker = CostTracker()

        tracker.track_request("claude-sonnet-4-20250514", 1000, 500, 0.01)
        tracker.track_request("claude-opus-4-20250514", 1000, 500, 0.05)
        tracker.track_request("claude-sonnet-4-20250514", 500, 250, 0.005)

        stats = tracker.get_stats()
        assert stats["requests_by_model"]["claude-sonnet-4-20250514"] == 2
        assert stats["requests_by_model"]["claude-opus-4-20250514"] == 1
        assert stats["cost_by_model"]["claude-sonnet-4-20250514"] == 0.015
        assert stats["cost_by_model"]["claude-opus-4-20250514"] == 0.05

    def test_reset(self):
        """Test resetting statistics."""
        tracker = CostTracker()
        tracker.track_request("claude-sonnet-4-20250514", 1000, 500, 0.01)

        tracker.reset()

        assert tracker.total_input_tokens == 0
        assert tracker.total_output_tokens == 0
        assert tracker.total_cost == 0.0
        assert len(tracker.requests) == 0

    def test_get_recent_requests(self):
        """Test getting recent requests."""
        tracker = CostTracker()

        for i in range(10):
            tracker.track_request("claude-sonnet-4-20250514", 100, 50, 0.001)

        recent = tracker.get_recent_requests(limit=5)
        assert len(recent) == 5

    def test_export_stats(self):
        """Test exporting detailed statistics."""
        tracker = CostTracker()
        tracker.track_request("claude-sonnet-4-20250514", 1000, 500, 0.01)

        exported = tracker.export_stats()
        assert "request_history" in exported
        assert len(exported["request_history"]) == 1
        assert exported["request_history"][0]["model"] == "claude-sonnet-4-20250514"


# ============================================================================
# ClaudeClient Tests (Mocked)
# ============================================================================


class TestClaudeClient:
    """Test suite for ClaudeClient with mocked API calls."""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create mock Anthropic client."""
        with patch("backend.llm.claude_client.AsyncAnthropic") as mock:
            yield mock

    @pytest.fixture
    def claude_client(self, mock_anthropic_client):
        """Create ClaudeClient with mocked API."""
        return ClaudeClient(
            api_key="test-api-key",
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
        )

    def test_client_initialization(self, claude_client):
        """Test client initializes correctly."""
        assert claude_client.model == "claude-sonnet-4-20250514"
        assert claude_client.max_tokens == 4096
        assert claude_client.temperature == 1.0
        assert isinstance(claude_client.rate_limiter, RateLimiter)
        assert isinstance(claude_client.cost_tracker, CostTracker)

    @pytest.mark.asyncio
    async def test_generate_completion(self, claude_client):
        """Test generating a completion."""
        # Mock response
        mock_message = Mock()
        mock_message.content = [Mock(text="Optimized resume text")]
        mock_message.model = "claude-sonnet-4-20250514"
        mock_message.usage = Mock(input_tokens=1000, output_tokens=500)
        mock_message.stop_reason = "end_turn"

        claude_client.client.messages.create = AsyncMock(return_value=mock_message)

        # Generate completion
        result = await claude_client.generate(
            prompt="Optimize this resume",
            system_prompt="You are a resume expert",
        )

        assert result["content"] == "Optimized resume text"
        assert result["model"] == "claude-sonnet-4-20250514"
        assert result["usage"]["input_tokens"] == 1000
        assert result["usage"]["output_tokens"] == 500
        assert result["cost"] > 0

    def test_calculate_cost(self, claude_client):
        """Test cost calculation."""
        # Sonnet-4 pricing: $3/M input, $15/M output
        cost = claude_client._calculate_cost(
            input_tokens=1000,
            output_tokens=500,
        )

        expected_cost = (1000 / 1_000_000) * 3.0 + (500 / 1_000_000) * 15.0
        assert abs(cost - expected_cost) < 0.0001

    def test_get_usage_stats(self, claude_client):
        """Test getting usage statistics."""
        # Manually track some usage
        claude_client.cost_tracker.track_request(
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
            cost=0.0105,
        )

        stats = claude_client.get_usage_stats()
        assert stats["total_requests"] == 1
        assert stats["total_input_tokens"] == 1000
        assert stats["total_cost"] == 0.0105

    def test_reset_usage_stats(self, claude_client):
        """Test resetting usage statistics."""
        claude_client.cost_tracker.track_request(
            "claude-sonnet-4-20250514", 1000, 500, 0.01
        )

        claude_client.reset_usage_stats()

        stats = claude_client.get_usage_stats()
        assert stats["total_requests"] == 0
        assert stats["total_cost"] == 0.0

    @pytest.mark.asyncio
    async def test_batch_generate(self, claude_client):
        """Test batch generation."""
        # Mock response
        mock_message = Mock()
        mock_message.content = [Mock(text="Optimized resume")]
        mock_message.model = "claude-sonnet-4-20250514"
        mock_message.usage = Mock(input_tokens=1000, output_tokens=500)
        mock_message.stop_reason = "end_turn"

        claude_client.client.messages.create = AsyncMock(return_value=mock_message)

        # Batch generate
        prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
        results = await claude_client.batch_generate(prompts, max_concurrent=2)

        assert len(results) == 3
        assert all(r["content"] == "Optimized resume" for r in results)


# ============================================================================
# PromptTemplates Tests
# ============================================================================


class TestPromptTemplates:
    """Test suite for PromptTemplates."""

    def test_get_system_prompt(self):
        """Test system prompt generation."""
        prompt = PromptTemplates.get_system_prompt()
        assert "ATS" in prompt
        assert "resume" in prompt.lower()
        assert len(prompt) > 100

    def test_generate_resume_optimization(self):
        """Test resume optimization prompt generation."""
        prompt = PromptTemplates.generate_resume_optimization(
            original_resume="Software Engineer with 5 years experience",
            job_description="Looking for Python expert",
            missing_keywords=["Python", "Django", "REST API"],
            suggestions=["Add metrics", "Highlight Python projects"],
            match_score=75.5,
            semantic_similarity=0.78,
        )

        assert "Software Engineer" in prompt
        assert "Python expert" in prompt
        assert "Python" in prompt
        assert "75.5%" in prompt
        assert "0.78" in prompt
        assert "Add metrics" in prompt

    def test_generate_cover_letter(self):
        """Test cover letter prompt generation."""
        prompt = PromptTemplates.generate_cover_letter(
            resume="Software Engineer resume",
            job_description="Python developer needed",
            company_name="Tech Corp",
            position_title="Senior Python Developer",
        )

        assert "Tech Corp" in prompt
        assert "Senior Python Developer" in prompt
        assert "cover letter" in prompt.lower()
        assert "Software Engineer" in prompt

    def test_analyze_job_description(self):
        """Test job description analysis prompt."""
        prompt = PromptTemplates.analyze_job_description(
            job_description="We need a Python developer with 5+ years experience"
        )

        assert "Python developer" in prompt
        assert "Required Skills" in prompt
        assert "Keywords" in prompt
        assert "analyze" in prompt.lower()

    def test_tailor_bullet_points(self):
        """Test bullet point tailoring prompt."""
        prompt = PromptTemplates.tailor_bullet_points(
            experience_bullets=[
                "Developed web applications",
                "Led team of 5 developers",
            ],
            job_requirements=[
                "Python expertise",
                "Team leadership",
            ],
        )

        assert "Developed web applications" in prompt
        assert "Led team of 5 developers" in prompt
        assert "Python expertise" in prompt
        assert "Team leadership" in prompt

    def test_extract_achievements(self):
        """Test achievement extraction prompt."""
        prompt = PromptTemplates.extract_achievements(
            experience_text="Worked on various projects improving system performance"
        )

        assert "improving system performance" in prompt
        assert "achievement" in prompt.lower()
        assert "Action verb" in prompt

    def test_validate_resume_quality(self):
        """Test resume quality validation prompt."""
        prompt = PromptTemplates.validate_resume_quality(
            resume="Software Engineer\nExperience: 5 years"
        )

        assert "Software Engineer" in prompt
        assert "ATS Compatibility" in prompt
        assert "Content Quality" in prompt
        assert "evaluate" in prompt.lower()


# ============================================================================
# Integration Tests
# ============================================================================


class TestLLMIntegration:
    """Integration tests for LLM module."""

    def test_cost_tracker_with_client(self):
        """Test cost tracker integration with client."""
        with patch("backend.llm.claude_client.AsyncAnthropic"):
            client = ClaudeClient(api_key="test-key")

            # Manually track usage
            client.cost_tracker.track_request(
                model="claude-sonnet-4-20250514",
                input_tokens=2000,
                output_tokens=1000,
                cost=0.021,
            )

            stats = client.get_usage_stats()
            assert stats["total_requests"] == 1
            assert stats["total_tokens"] == 3000

    def test_prompt_template_with_real_data(self):
        """Test prompt templates with realistic data."""
        resume = """John Doe
Software Engineer
Experience:
- Developed Python applications for 5 years
- Led team of 3 developers"""

        jd = """Senior Python Developer
Requirements:
- 5+ years Python experience
- Django, FastAPI
- Team leadership"""

        prompt = PromptTemplates.generate_resume_optimization(
            original_resume=resume,
            job_description=jd,
            missing_keywords=["Django", "FastAPI"],
            suggestions=["Add web framework experience", "Quantify team size"],
            match_score=70.0,
            semantic_similarity=0.75,
        )

        # Verify all key elements are present
        assert "John Doe" in prompt
        assert "Senior Python Developer" in prompt
        assert "Django" in prompt
        assert "FastAPI" in prompt
        assert "70.0%" in prompt
