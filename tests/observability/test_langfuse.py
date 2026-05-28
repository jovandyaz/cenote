# SPDX-License-Identifier: Apache-2.0
"""Tests for LangfuseTracer + LangfuseSpanContext."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cenote.observability import Tracer
from cenote.observability.langfuse import LangfuseTracer


def _fake_client() -> MagicMock:
    """Build a MagicMock that mimics langfuse.Langfuse client surface."""
    client = MagicMock()
    client.span.return_value = MagicMock()
    client.generation.return_value = MagicMock()
    return client


@pytest.mark.asyncio
class TestLangfuseTracer:
    async def test_satisfies_protocol(self) -> None:
        tracer: Tracer = LangfuseTracer(_fake_client())
        assert callable(tracer.span)

    async def test_non_llm_span_creates_span_observation(self) -> None:
        client = _fake_client()
        tracer = LangfuseTracer(client)
        async with tracer.span("embed"):
            pass
        client.span.assert_called_once()
        client.generation.assert_not_called()

    async def test_llm_prefix_creates_generation_observation(self) -> None:
        client = _fake_client()
        tracer = LangfuseTracer(client)
        async with tracer.span("llm.complete"):
            pass
        client.generation.assert_called_once()
        client.span.assert_not_called()

    async def test_set_attribute_forwarded(self) -> None:
        client = _fake_client()
        obs = MagicMock()
        client.generation.return_value = obs
        tracer = LangfuseTracer(client)
        async with tracer.span("llm.complete") as span:
            span.set_attribute("gen_ai.request.model", "claude-sonnet-4-6")
            span.set_attribute("gen_ai.usage.input_tokens", 1024)
        obs.update.assert_called()
        call_kwargs = obs.update.call_args_list
        all_kwargs: dict[str, object] = {}
        for call in call_kwargs:
            all_kwargs.update(call.kwargs)
        assert all_kwargs.get("model") == "claude-sonnet-4-6"
        assert all_kwargs.get("input_tokens") == 1024

    async def test_record_exception_sets_error_level(self) -> None:
        client = _fake_client()
        obs = MagicMock()
        client.span.return_value = obs
        tracer = LangfuseTracer(client)
        async with tracer.span("embed") as span:
            span.record_exception(RuntimeError("boom"))
        obs.update.assert_called()
        merged: dict[str, object] = {}
        for call in obs.update.call_args_list:
            merged.update(call.kwargs)
        assert merged.get("level") == "ERROR"
        assert "boom" in str(merged.get("status_message", ""))

    async def test_unknown_attribute_goes_to_metadata(self) -> None:
        client = _fake_client()
        obs = MagicMock()
        client.span.return_value = obs
        tracer = LangfuseTracer(client)
        async with tracer.span("embed") as span:
            span.set_attribute("custom.thing", "value")
        merged: dict[str, object] = {}
        for call in obs.update.call_args_list:
            merged.update(call.kwargs)
        metadata = merged.get("metadata", {})
        assert isinstance(metadata, dict)
        assert metadata.get("custom.thing") == "value"
