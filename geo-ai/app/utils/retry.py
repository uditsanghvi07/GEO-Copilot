"""Retry/timeout decorator for every external call (LLM, website fetch,
Play Store fetch, etc.).

Wraps an async callable with a timeout and exponential backoff retry (max 3
attempts by default). On final failure it raises `ExternalServiceError`
rather than the raw exception, so callers (agents) can catch one known type
and degrade gracefully instead of crashing the whole pipeline.
"""

import asyncio
import functools
from typing import Any, Awaitable, Callable, TypeVar

from loguru import logger

from app.utils.exceptions import ExternalServiceError

T = TypeVar("T")


def with_retry_and_timeout(
    timeout_seconds: float = 30.0,
    max_attempts: int = 3,
    base_delay_seconds: float = 1.0,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorate an async function with timeout handling and exponential
    backoff retry.

    Inputs: timeout_seconds per attempt, max_attempts, base_delay_seconds
        (delay doubles each retry: base, 2*base, 4*base, ...).
    Outputs: a wrapped async function that either returns the original
        function's result or raises `ExternalServiceError` after exhausting
        all attempts.
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
                except Exception as exc:  # noqa: BLE001 - intentionally broad, we classify below
                    last_error = exc
                    logger.warning(
                        f"{func.__module__}.{func.__qualname__} attempt {attempt}/{max_attempts} "
                        f"failed: {exc!r}"
                    )
                    if attempt < max_attempts:
                        delay = base_delay_seconds * (2 ** (attempt - 1))
                        await asyncio.sleep(delay)

            logger.error(
                f"{func.__module__}.{func.__qualname__} failed after {max_attempts} attempts: "
                f"{last_error!r}"
            )
            raise ExternalServiceError(
                f"{func.__qualname__} failed after {max_attempts} attempts: {last_error}"
            ) from last_error

        return wrapper

    return decorator
