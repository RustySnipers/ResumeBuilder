"""
Retry Logic - Phase 3.2

Implements exponential backoff retry logic for LLM API calls.
"""

import asyncio
import logging
from typing import TypeVar, Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry logic."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds before first retry
            max_delay: Maximum delay in seconds between retries
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delays
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


async def retry_with_exponential_backoff(
    func: Callable[..., Any],
    config: Optional[RetryConfig] = None,
    *args,
    **kwargs
) -> Any:
    """
    Retry async function with exponential backoff.

    Args:
        func: Async function to retry
        config: RetryConfig instance (uses defaults if None)
        *args: Arguments to pass to function
        **kwargs: Keyword arguments to pass to function

    Returns:
        Result from successful function call

    Raises:
        Exception: Last exception if all retries exhausted
    """
    if config is None:
        config = RetryConfig()

    last_exception = None

    for attempt in range(config.max_retries + 1):
        try:
            result = await func(*args, **kwargs)
            if attempt > 0:
                logger.info(f"Retry succeeded on attempt {attempt + 1}")
            return result

        except Exception as e:
            last_exception = e

            # Don't retry on last attempt
            if attempt >= config.max_retries:
                logger.error(
                    f"All {config.max_retries} retry attempts exhausted. "
                    f"Last error: {str(e)}"
                )
                break

            # Calculate delay with exponential backoff
            delay = min(
                config.initial_delay * (config.exponential_base ** attempt),
                config.max_delay
            )

            # Add jitter if enabled
            if config.jitter:
                import random
                delay = delay * (0.5 + random.random())

            logger.warning(
                f"Attempt {attempt + 1} failed: {str(e)}. "
                f"Retrying in {delay:.2f}s..."
            )

            await asyncio.sleep(delay)

    # All retries exhausted, raise last exception
    raise last_exception


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for adding retry logic to async functions.

    Args:
        config: RetryConfig instance (uses defaults if None)

    Example:
        @with_retry(RetryConfig(max_retries=3))
        async def my_function():
            # Function that might fail
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_with_exponential_backoff(
                func, config, *args, **kwargs
            )
        return wrapper
    return decorator
