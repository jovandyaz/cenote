"""Tests for cenote.embedders._http.RateLimiter."""

from __future__ import annotations

import asyncio
import time

import pytest

from cenote.embedders._http import RateLimiter


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
        # Use 2 RPM with a 200ms window so the 3rd request waits ~200ms.
        limiter = RateLimiter(requests_per_minute=2)
        limiter._window_s = 0.2  # 200ms window
        start = time.monotonic()
        for _ in range(3):
            async with limiter:
                pass
        elapsed = time.monotonic() - start
        assert elapsed >= 0.2, f"expected ≥200ms throttle, got {elapsed:.3f}s"

    async def test_concurrent_callers_serialized(self) -> None:
        limiter = RateLimiter(requests_per_minute=10)
        limiter._window_s = 0.5

        async def task() -> None:
            async with limiter:
                pass

        await asyncio.gather(*[task() for _ in range(5)])
        # 5 in budget → no throttle expected; no exception is the assertion.

    async def test_negative_rpm_rejected(self) -> None:
        with pytest.raises(ValueError):
            RateLimiter(requests_per_minute=0)
        with pytest.raises(ValueError):
            RateLimiter(requests_per_minute=-1)
