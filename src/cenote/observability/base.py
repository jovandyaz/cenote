# SPDX-License-Identifier: Apache-2.0
"""Tracer Protocol + no-op default. M1.1 will add OTel and Langfuse adapters."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class Tracer(Protocol):
    """Wraps operations for observability; implementations stream span events to
    an external system. NoopTracer does nothing when no tracer is injected.
    """

    def span(
        self, name: str, attributes: dict[str, Any] | None = None
    ) -> AbstractAsyncContextManager[None]: ...


class NoopTracer:
    """Default tracer — drops all spans. Use when no observability is wired in."""

    @asynccontextmanager
    async def span(
        self, name: str, attributes: dict[str, Any] | None = None
    ) -> AsyncIterator[None]:
        yield
