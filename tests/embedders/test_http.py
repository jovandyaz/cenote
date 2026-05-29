"""Tests for cenote.embedders._http.RateLimiter."""

from __future__ import annotations

import asyncio
import time

import pytest
from aiolimiter import AsyncLimiter

from cenote.embedders._http import RateLimiter
from cenote.errors import ConfigurationError


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
    import asyncio

    import httpx

    from cenote.embedders._http import retrying

    sleep_durations: list[float] = []

    async def _make_429() -> httpx.Response:
        req = httpx.Request("POST", "https://example.invalid")
        resp = httpx.Response(429, request=req)
        raise httpx.HTTPStatusError("rate limited", request=req, response=resp)

    original_sleep = asyncio.sleep

    async def recording_sleep(seconds: float) -> None:
        sleep_durations.append(seconds)
        await original_sleep(0)

    asyncio.sleep = recording_sleep  # type: ignore[assignment]
    try:
        results = await asyncio.gather(
            retrying(_make_429, max_retries=2, base_backoff_seconds=0.1),
            retrying(_make_429, max_retries=2, base_backoff_seconds=0.1),
            return_exceptions=True,
        )
    finally:
        asyncio.sleep = original_sleep  # type: ignore[assignment]

    assert all(isinstance(r, BaseException) for r in results)
    rounded = {round(s, 4) for s in sleep_durations}
    assert len(sleep_durations) >= 4, f"expected >=4 sleeps, got {sleep_durations}"
    assert len(rounded) >= 2, f"no jitter detected: {sleep_durations}"
