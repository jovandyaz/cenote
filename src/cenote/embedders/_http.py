# SPDX-License-Identifier: Apache-2.0
"""Shared HTTP helpers — retry with exponential backoff + per-RPM rate limiting."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable
from types import TracebackType

import httpx

RETRY_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})


class RateLimiter:
    """Sliding-window rate limiter — at most `requests_per_minute` in any 60s window.

    Usage:
        limiter = RateLimiter(requests_per_minute=300)
        async with limiter:
            await client.post(...)
    """

    def __init__(self, requests_per_minute: int) -> None:
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        self._rpm = requests_per_minute
        self._window_s = 60.0
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> RateLimiter:
        async with self._lock:
            now = time.monotonic()
            while self._timestamps and now - self._timestamps[0] >= self._window_s:
                self._timestamps.popleft()
            if len(self._timestamps) >= self._rpm:
                wait_for = self._window_s - (now - self._timestamps[0])
                await asyncio.sleep(max(wait_for, 0.0))
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] >= self._window_s:
                    self._timestamps.popleft()
            self._timestamps.append(time.monotonic())
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


async def retrying(
    fn: Callable[[], Awaitable[httpx.Response]],
    *,
    max_retries: int,
    base_backoff_seconds: float,
) -> httpx.Response:
    """Call `fn` with exponential backoff on transient HTTP errors.

    Returns the first successful response or re-raises the final HTTPStatusError
    after `max_retries` attempts on RETRY_STATUSES.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = await fn()
            if response.status_code not in RETRY_STATUSES:
                response.raise_for_status()
                return response
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response.status_code not in RETRY_STATUSES:
                raise
            if attempt == max_retries:
                raise
            await asyncio.sleep(base_backoff_seconds * (2**attempt))
    assert last_exc is not None
    raise last_exc
