# SPDX-License-Identifier: Apache-2.0
"""Tracer + SpanContext Protocols + no-op defaults."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any, Protocol


class SpanContext(Protocol):
    """Active span handle. Adapters bridge to OTel/Langfuse span APIs."""

    def set_attribute(self, key: str, value: Any) -> None:
        """Attach a key/value attribute to the active span."""
        ...

    def record_exception(self, exception: BaseException) -> None:
        """Record an exception against the active span (does not raise)."""
        ...


class Tracer(Protocol):
    """Wraps operations for observability. Implementations stream span events
    to an external system; NoopTracer drops them.
    """

    def span(
        self, name: str, attributes: dict[str, Any] | None = None
    ) -> AbstractAsyncContextManager[SpanContext]: ...


class NoopSpanContext:
    """SpanContext that drops every call. Shared singleton via `_NOOP_SPAN`."""

    def set_attribute(self, key: str, value: Any) -> None:
        return None

    def record_exception(self, exception: BaseException) -> None:
        return None


_NOOP_SPAN = NoopSpanContext()


class NoopTracer:
    """Default tracer — drops all spans. Use when no observability is wired in."""

    @asynccontextmanager
    async def span(
        self, name: str, attributes: dict[str, Any] | None = None
    ) -> AsyncIterator[SpanContext]:
        yield _NOOP_SPAN
