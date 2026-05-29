"""Tests for cenote.embedders._http.RateLimiter."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC

import httpx
import pytest
from aiolimiter import AsyncLimiter

from cenote.embedders._http import RateLimiter, retrying
from cenote.errors import ConfigurationError


@asynccontextmanager
async def record_sleeps() -> AsyncIterator[list[float]]:
    """Monkey-patch asyncio.sleep with a fast recorder; yields the captured durations."""
    captured: list[float] = []
    original = asyncio.sleep

    async def recorder(seconds: float) -> None:
        captured.append(seconds)
        await original(0)

    asyncio.sleep = recorder  # type: ignore[assignment]
    try:
        yield captured
    finally:
        asyncio.sleep = original  # type: ignore[assignment]


def fail_once_then_succeed(
    status: int, headers: dict[str, str] | None = None
) -> Callable[[], Awaitable[httpx.Response]]:
    """First call raises HTTPStatusError(`status`, `headers`); subsequent calls return 200."""
    state = {"n": 0}
    req = httpx.Request("POST", "https://example.invalid")

    async def _fn() -> httpx.Response:
        state["n"] += 1
        if state["n"] == 1:
            resp = httpx.Response(status, headers=headers or {}, request=req)
            raise httpx.HTTPStatusError("transient", request=req, response=resp)
        return httpx.Response(200, request=req)

    return _fn


class TestRateLimiter:
    async def test_under_limit_no_throttle(self) -> None:
        limiter = RateLimiter(requests_per_minute=600)  # 10/sec
        start = time.monotonic()
        for _ in range(5):
            async with limiter:
                pass
        elapsed = time.monotonic() - start
        assert elapsed < 0.5, f"unexpected throttle: {elapsed:.3f}s"

    async def test_at_limit_throttles(self) -> None:
        # Swap in a fast-window limiter to keep the test sub-second: 2 entries
        # per 200ms window, so the 3rd acquire must wait ~100ms (leaky-bucket).
        limiter = RateLimiter(requests_per_minute=2)
        limiter._limiter = AsyncLimiter(max_rate=2, time_period=0.2)
        start = time.monotonic()
        for _ in range(3):
            async with limiter:
                pass
        elapsed = time.monotonic() - start
        assert elapsed >= 0.08, f"expected throttle >=80ms, got {elapsed:.3f}s"

    async def test_concurrent_callers_within_budget(self) -> None:
        limiter = RateLimiter(requests_per_minute=10)
        limiter._limiter = AsyncLimiter(max_rate=10, time_period=0.5)

        async def task() -> None:
            async with limiter:
                pass

        await asyncio.gather(*[task() for _ in range(5)])

    async def test_negative_rpm_rejected(self) -> None:
        with pytest.raises(ConfigurationError):
            RateLimiter(requests_per_minute=0)
        with pytest.raises(ConfigurationError):
            RateLimiter(requests_per_minute=-1)


@pytest.mark.asyncio
async def test_retrying_applies_jitter_to_backoff() -> None:
    """Two concurrent retries should NOT sleep identical durations (jitter active)."""

    async def _make_429() -> httpx.Response:
        req = httpx.Request("POST", "https://example.invalid")
        resp = httpx.Response(429, request=req)
        raise httpx.HTTPStatusError("rate limited", request=req, response=resp)

    async with record_sleeps() as sleeps:
        results = await asyncio.gather(
            retrying(_make_429, max_retries=2, base_backoff_seconds=0.1),
            retrying(_make_429, max_retries=2, base_backoff_seconds=0.1),
            return_exceptions=True,
        )

    assert all(isinstance(r, BaseException) for r in results)
    assert len(sleeps) >= 4, f"expected >=4 sleeps, got {sleeps}"
    assert len({round(s, 4) for s in sleeps}) >= 2, f"no jitter detected: {sleeps}"


@pytest.mark.asyncio
async def test_retrying_honors_retry_after_seconds_on_429() -> None:
    """A numeric Retry-After header must override the exponential backoff."""
    fn = fail_once_then_succeed(429, {"retry-after": "7"})
    async with record_sleeps() as sleeps:
        await retrying(fn, max_retries=3, base_backoff_seconds=0.1)
    assert any(abs(s - 7.0) < 0.001 for s in sleeps), (
        f"expected a 7.0s sleep from Retry-After, saw {sleeps}"
    )


@pytest.mark.asyncio
async def test_retrying_honors_retry_after_http_date_on_429() -> None:
    """Retry-After as an HTTP-date (RFC 7231) must be parsed to a wait delta."""
    from datetime import datetime, timedelta
    from email.utils import format_datetime

    target = datetime.now(UTC) + timedelta(seconds=5)
    fn = fail_once_then_succeed(429, {"retry-after": format_datetime(target, usegmt=True)})
    async with record_sleeps() as sleeps:
        await retrying(fn, max_retries=3, base_backoff_seconds=0.1)
    assert any(3.0 <= s <= 6.0 for s in sleeps), (
        f"expected a ~5s sleep from HTTP-date Retry-After, saw {sleeps}"
    )


@pytest.mark.asyncio
async def test_retrying_honors_retry_after_on_503() -> None:
    """Retry-After applies to any retryable status, not just 429 (RFC 7231)."""
    fn = fail_once_then_succeed(503, {"retry-after": "3"})
    async with record_sleeps() as sleeps:
        await retrying(fn, max_retries=3, base_backoff_seconds=0.1)
    assert any(abs(s - 3.0) < 0.001 for s in sleeps), (
        f"expected a 3.0s sleep from 503 Retry-After, saw {sleeps}"
    )


@pytest.mark.asyncio
async def test_retrying_ignores_malformed_retry_after() -> None:
    """A garbage Retry-After value must NOT crash; fall back to exponential+jitter."""
    fn = fail_once_then_succeed(429, {"retry-after": "nonsense"})
    async with record_sleeps() as sleeps:
        await retrying(fn, max_retries=3, base_backoff_seconds=0.25)
    assert sleeps, "expected at least one sleep on retry"
    assert all(s < 5.0 for s in sleeps), (
        f"malformed Retry-After must NOT be parsed as a long wait, saw {sleeps}"
    )
