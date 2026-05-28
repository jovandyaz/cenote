# SPDX-License-Identifier: Apache-2.0
"""Tests for the Tracer / SpanContext Protocols + NoopTracer / NoopSpanContext."""

from __future__ import annotations

import pytest

from cenote.observability import NoopSpanContext, NoopTracer, SpanContext, Tracer


def test_noop_tracer_satisfies_protocol() -> None:
    tracer: Tracer = NoopTracer()
    assert callable(tracer.span)


def test_noop_span_context_satisfies_protocol() -> None:
    ctx: SpanContext = NoopSpanContext()
    assert callable(ctx.set_attribute)
    assert callable(ctx.record_exception)


def test_noop_span_context_set_attribute_is_silent() -> None:
    ctx = NoopSpanContext()
    ctx.set_attribute("k", "v")
    ctx.set_attribute("count", 42)
    ctx.set_attribute("ratio", 0.5)


def test_noop_span_context_record_exception_is_silent() -> None:
    ctx = NoopSpanContext()
    ctx.record_exception(RuntimeError("boom"))
    ctx.record_exception(ValueError("also boom"))


@pytest.mark.asyncio
async def test_noop_tracer_yields_span_context() -> None:
    tracer = NoopTracer()
    async with tracer.span("op") as span:
        assert isinstance(span, NoopSpanContext)
        span.set_attribute("anything", 1)


@pytest.mark.asyncio
async def test_noop_tracer_span_with_attributes_arg() -> None:
    tracer = NoopTracer()
    async with tracer.span("op", attributes={"k": "v"}) as span:
        assert isinstance(span, NoopSpanContext)
