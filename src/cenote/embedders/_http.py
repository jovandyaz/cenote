# SPDX-License-Identifier: Apache-2.0
"""Shared HTTP helpers — retry with exponential backoff + per-RPM rate limiting."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from types import TracebackType

import httpx
import stamina
from aiolimiter import AsyncLimiter

from cenote.errors import ConfigurationError, RateLimitError

logger = logging.getLogger(__name__)

RETRY_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})


class RateLimiter:
    """Async rate limiter — at most `requests_per_minute` in any 60s window.

    Thin wrapper around aiolimiter.AsyncLimiter (leaky-bucket algorithm).
    Usage:
        limiter = RateLimiter(requests_per_minute=300)
        async with limiter:
            await client.post(...)
    """

    def __init__(self, requests_per_minute: int) -> None:
        if requests_per_minute <= 0:
            raise ConfigurationError("requests_per_minute must be positive")
        self._limiter = AsyncLimiter(max_rate=requests_per_minute, time_period=60.0)

    async def __aenter__(self) -> RateLimiter:
        await self._limiter.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


def _parse_retry_after(header: str | None) -> float | None:
    """Parse an HTTP Retry-After header (RFC 7231 §7.1.3): seconds or HTTP-date.

    Returns the wait duration in seconds, or None when the header is absent or
    unparseable. Negative deltas (date already in the past) are clamped to 0.
    """
    if not header:
        return None
    raw = header.strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        pass
    try:
        target = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if target.tzinfo is None:
        target = target.replace(tzinfo=UTC)
    return max(0.0, (target - datetime.now(UTC)).total_seconds())


def _retry_hook(exc: BaseException) -> bool | float:
    """stamina backoff hook — retry on RETRY_STATUSES, override delay with Retry-After.

    Returning a float makes stamina use that exact wait (no exp/jitter applied);
    returning True keeps stamina's configured exponential schedule.
    """
    if not isinstance(exc, httpx.HTTPStatusError):
        return False
    if exc.response.status_code not in RETRY_STATUSES:
        return False
    retry_after = _parse_retry_after(exc.response.headers.get("retry-after"))
    return retry_after if retry_after is not None else True


async def retrying(
    fn: Callable[[], Awaitable[httpx.Response]],
    *,
    max_retries: int,
    base_backoff_seconds: float,
) -> httpx.Response:
    """Call `fn` with exponential backoff + jitter on transient HTTP errors.

    Retries only on RETRY_STATUSES; non-retryable HTTPStatusError propagates
    immediately. When the response carries a Retry-After header, that value
    (seconds or HTTP-date) overrides the computed backoff. After exhausting
    retries on 429, raises RateLimitError; otherwise re-raises the original
    HTTPStatusError.
    """
    try:
        async for attempt in stamina.retry_context(
            on=_retry_hook,
            attempts=max_retries + 1,
            wait_initial=base_backoff_seconds,
            wait_jitter=base_backoff_seconds * 0.5,
            wait_exp_base=2,
        ):
            with attempt:
                response = await fn()
                response.raise_for_status()
                return response
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            raise RateLimitError(str(exc)) from exc
        raise
    raise RuntimeError("unreachable: stamina retry_context guarantees return or raise")
