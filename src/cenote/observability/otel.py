# SPDX-License-Identifier: Apache-2.0
"""OTelTracer — bridges the Tracer Protocol to OpenTelemetry."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

try:
    from opentelemetry.trace import Span as _OTelSpan
    from opentelemetry.trace import Tracer as _OTelTracerType
except ImportError as exc:
    raise ImportError(
        "OTel support requires the [otel] extra: pip install cenote-core[otel]"
    ) from exc


class OTelSpanContext:
    """Bridges OTel span API to the SpanContext Protocol."""

    def __init__(self, span: _OTelSpan) -> None:
        self._span = span

    def set_attribute(self, key: str, value: Any) -> None:
        self._span.set_attribute(key, value)

    def record_exception(self, exception: BaseException) -> None:
        self._span.record_exception(exception)


class OTelTracer:
    """Adapts an `opentelemetry.trace.Tracer` to the cenote `Tracer` Protocol."""

    def __init__(self, tracer: _OTelTracerType) -> None:
        self._tracer = tracer

    @asynccontextmanager
    async def span(
        self, name: str, attributes: dict[str, Any] | None = None
    ) -> AsyncIterator[OTelSpanContext]:
        with self._tracer.start_as_current_span(name, attributes=attributes) as span:
            yield OTelSpanContext(span)


__all__ = ["OTelSpanContext", "OTelTracer"]
