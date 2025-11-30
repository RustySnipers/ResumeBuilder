"""
Claude Client - Phase 3.1

Async wrapper for Anthropic Claude API with streaming support,
rate limiting, and cost tracking.
"""

import asyncio
import logging
from typing import Optional, AsyncGenerator, Dict, Any, List
from datetime import datetime, timedelta
from anthropic import AsyncAnthropic
from anthropic.types import Message, MessageStreamEvent
from backend.llm.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Implements token bucket algorithm to ensure we don't exceed
    Anthropic API rate limits.
    """

    def __init__(self, max_requests_per_minute: int = 50):
        """
        Initialize rate limiter.

        Args:
            max_requests_per_minute: Maximum requests allowed per minute
        """
        self.max_requests = max_requests_per_minute
        self.tokens = max_requests_per_minute
        self.last_refill = datetime.utcnow()
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire permission to make an API call.

        Blocks if rate limit would be exceeded.
        """
        async with self.lock:
            await self._refill_tokens()

            while self.tokens < 1:
                # Wait for tokens to refill
                await asyncio.sleep(0.1)
                await self._refill_tokens()

            self.tokens -= 1

    async def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = datetime.utcnow()
        time_passed = (now - self.last_refill).total_seconds()

        # Refill rate: max_requests per 60 seconds
        tokens_to_add = (time_passed / 60.0) * self.max_requests

        if tokens_to_add > 0:
            self.tokens = min(self.max_requests, self.tokens + tokens_to_add)
            self.last_refill = now


class ClaudeClient:
    """
    Async client for Anthropic Claude API.

    Features:
    - Async API calls with retry logic
    - Streaming support for real-time generation
    - Rate limiting to prevent quota exhaustion
    - Cost tracking for budget management
    - Response validation and error handling
    """

    # Anthropic pricing (as of 2025, per million tokens)
    PRICING = {
        "claude-sonnet-4-20250514": {
            "input": 3.00,   # $3 per million input tokens
            "output": 15.00,  # $15 per million output tokens
        },
        "claude-opus-4-20250514": {
            "input": 15.00,   # $15 per million input tokens
            "output": 75.00,  # $75 per million output tokens
        },
        "claude-3-5-sonnet-20241022": {
            "input": 3.00,
            "output": 15.00,
        },
    }

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float = 1.0,
        max_requests_per_minute: int = 50,
    ):
        """
        Initialize Claude client.

        Args:
            api_key: Anthropic API key
            model: Claude model to use (default: claude-sonnet-4-20250514)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            max_requests_per_minute: Rate limit for API calls
        """
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.rate_limiter = RateLimiter(max_requests_per_minute)
        self.cost_tracker = CostTracker()

        logger.info(f"Initialized ClaudeClient with model: {model}")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generate completion from Claude (non-streaming).

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Override default max_tokens
            temperature: Override default temperature

        Returns:
            Dict containing:
                - content: Generated text
                - model: Model used
                - usage: Token usage statistics
                - cost: Estimated cost in USD
                - finish_reason: Why generation stopped
        """
        await self.rate_limiter.acquire()

        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
                system=system_prompt or "",
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            # Extract response
            content = message.content[0].text if message.content else ""

            # Calculate cost
            cost = self._calculate_cost(
                message.usage.input_tokens,
                message.usage.output_tokens,
            )

            # Track usage
            self.cost_tracker.track_request(
                model=self.model,
                input_tokens=message.usage.input_tokens,
                output_tokens=message.usage.output_tokens,
                cost=cost,
            )

            logger.info(
                f"Generated {message.usage.output_tokens} tokens "
                f"(cost: ${cost:.4f})"
            )

            return {
                "content": content,
                "model": message.model,
                "usage": {
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                },
                "cost": cost,
                "finish_reason": message.stop_reason,
            }

        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate completion from Claude with streaming.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Override default max_tokens
            temperature: Override default temperature

        Yields:
            Text chunks as they're generated
        """
        await self.rate_limiter.acquire()

        input_tokens = 0
        output_tokens = 0

        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
                system=system_prompt or "",
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            ) as stream:
                async for event in stream:
                    # Track token usage
                    if hasattr(event, "message") and hasattr(event.message, "usage"):
                        input_tokens = event.message.usage.input_tokens

                    # Yield text deltas
                    if hasattr(event, "delta") and hasattr(event.delta, "text"):
                        yield event.delta.text

                # Get final message for token counts
                final_message = await stream.get_final_message()
                output_tokens = final_message.usage.output_tokens

                # Calculate and track cost
                cost = self._calculate_cost(input_tokens, output_tokens)
                self.cost_tracker.track_request(
                    model=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=cost,
                )

                logger.info(
                    f"Streamed {output_tokens} tokens (cost: ${cost:.4f})"
                )

        except Exception as e:
            logger.error(f"Error streaming completion: {e}")
            raise

    async def batch_generate(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_concurrent: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate completions for multiple prompts concurrently.

        Args:
            prompts: List of user prompts
            system_prompt: Optional system prompt
            max_tokens: Override default max_tokens
            temperature: Override default temperature
            max_concurrent: Maximum concurrent requests

        Returns:
            List of response dictionaries
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_semaphore(prompt: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

        tasks = [generate_with_semaphore(p) for p in prompts]
        return await asyncio.gather(*tasks)

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate estimated cost for a request.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        if self.model not in self.PRICING:
            logger.warning(f"Unknown model pricing: {self.model}, using default")
            pricing = self.PRICING["claude-sonnet-4-20250514"]
        else:
            pricing = self.PRICING[self.model]

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics and costs.

        Returns:
            Dictionary with usage statistics
        """
        return self.cost_tracker.get_stats()

    def reset_usage_stats(self) -> None:
        """Reset usage statistics."""
        self.cost_tracker.reset()
