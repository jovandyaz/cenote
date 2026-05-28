# SPDX-License-Identifier: Apache-2.0
"""Tests for OTelTracer + OTelSpanContext."""

from __future__ import annotations

from typing import Any

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from cenote.models import Chunk, EmbeddedChunk
from cenote.observability import SpanContext, Tracer
from cenote.observability.otel import OTelTracer
from cenote.observability.wrappers import TracedEmbedder
from tests._factories import make_chunk


@pytest.fixture
def tracer_setup() -> tuple[OTelTracer, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    otel_tracer = provider.get_tracer(__name__)
    return OTelTracer(otel_tracer), exporter


@pytest.mark.asyncio
class TestOTelTracer:
    async def test_satisfies_protocol(
        self, tracer_setup: tuple[OTelTracer, InMemorySpanExporter]
    ) -> None:
        tracer, _ = tracer_setup
        as_protocol: Tracer = tracer
        assert callable(as_protocol.span)

    async def test_emits_span_with_name(
        self, tracer_setup: tuple[OTelTracer, InMemorySpanExporter]
    ) -> None:
        tracer, exporter = tracer_setup
        async with tracer.span("test-op"):
            pass
        spans = exporter.get_finished_spans()
        assert any(s.name == "test-op" for s in spans)

    async def test_set_attribute_is_recorded(
        self, tracer_setup: tuple[OTelTracer, InMemorySpanExporter]
    ) -> None:
        tracer, exporter = tracer_setup
        async with tracer.span("with-attr") as span:
            assert hasattr(span, "set_attribute") and hasattr(span, "record_exception")
            _: SpanContext = span
            span.set_attribute("model", "voyage-3")
            span.set_attribute("batch_size", 16)
        finished = next(s for s in exporter.get_finished_spans() if s.name == "with-attr")
        assert finished.attributes is not None
        assert finished.attributes.get("model") == "voyage-3"
        assert finished.attributes.get("batch_size") == 16

    async def test_record_exception_is_recorded(
        self, tracer_setup: tuple[OTelTracer, InMemorySpanExporter]
    ) -> None:
        tracer, exporter = tracer_setup
        async with tracer.span("with-exc") as span:
            span.record_exception(RuntimeError("boom"))
        finished = next(s for s in exporter.get_finished_spans() if s.name == "with-exc")
        exc_events = [e for e in finished.events if e.name == "exception"]
        assert len(exc_events) == 1
        attrs = exc_events[0].attributes
        assert attrs is not None
        assert attrs.get("exception.type") == "RuntimeError"
        assert attrs.get("exception.message") == "boom"

    async def test_initial_attributes_passed_through(
        self, tracer_setup: tuple[OTelTracer, InMemorySpanExporter]
    ) -> None:
        tracer, exporter = tracer_setup
        async with tracer.span("init-attrs", attributes={"foo": "bar"}):
            pass
        finished = next(s for s in exporter.get_finished_spans() if s.name == "init-attrs")
        assert finished.attributes is not None
        assert finished.attributes.get("foo") == "bar"


class _StubEmbedder:
    model_id = "mock:default"
    dimensions = 2

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        return [
            EmbeddedChunk(
                chunk=c,
                embedding=[0.1, 0.2],
                embedding_model=self.model_id,
                dimensions=self.dimensions,
            )
            for c in chunks
        ]

    async def embed_query(self, query: str) -> list[float]:
        return [0.1, 0.2]


@pytest.mark.asyncio
async def test_traced_embedder_emits_to_otel(
    tracer_setup: tuple[OTelTracer, InMemorySpanExporter],
) -> None:
    """End-to-end: TracedEmbedder wired to OTelTracer emits spans with attrs."""
    tracer, exporter = tracer_setup
    embedder = TracedEmbedder(_StubEmbedder(), tracer)
    await embedder.embed([make_chunk("hello"), make_chunk("world", idx=1)])
    finished = next(s for s in exporter.get_finished_spans() if s.name == "embedder.embed")
    attrs: Any = finished.attributes
    assert attrs is not None
    assert attrs.get("gen_ai.request.model") == "mock:default"
    assert attrs.get("batch_size") == 2
