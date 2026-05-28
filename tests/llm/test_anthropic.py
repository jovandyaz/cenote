# SPDX-License-Identifier: Apache-2.0
"""Tests for AnthropicLLM — respx-mocked HTTP, no real API calls."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from cenote.errors import ConfigurationError, RateLimitError
from cenote.llm.anthropic import AnthropicLLM
from cenote.models import Message
from tests._stubs import StubTracer

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


def _ok_response(
    text: str = "hola mundo",
    *,
    cache_read: int = 0,
    cache_creation: int = 0,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": "claude-sonnet-4-6",
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 12,
                "output_tokens": 7,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_creation,
            },
        },
    )


def _sse_stream_response() -> httpx.Response:
    """Build a 7-event SSE response that yields 'hola mundo' as two text deltas."""
    events: list[tuple[str, dict[str, Any]]] = [
        (
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "m",
                    "type": "message",
                    "role": "assistant",
                    "model": "claude-sonnet-4-6",
                    "content": [],
                    "stop_reason": None,
                    "usage": {
                        "input_tokens": 3,
                        "output_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "cache_creation_input_tokens": 0,
                    },
                },
            },
        ),
        (
            "content_block_start",
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
        ),
        (
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "hola "},
            },
        ),
        (
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "mundo"},
            },
        ),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        (
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn"},
                "usage": {"output_tokens": 5},
            },
        ),
        ("message_stop", {"type": "message_stop"}),
    ]
    body = "".join(
        f"event: {name}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"
        for name, payload in events
    )
    return httpx.Response(
        200,
        headers={"content-type": "text/event-stream"},
        content=body.encode("utf-8"),
    )


@pytest.mark.asyncio
class TestAnthropicLLM:
    async def test_rejects_missing_api_key(self) -> None:
        with pytest.raises(ConfigurationError):
            AnthropicLLM(api_key="")

    async def test_model_id_format(self) -> None:
        llm = AnthropicLLM(api_key="k", model="claude-sonnet-4-6")
        assert llm.model_id == "anthropic:claude-sonnet-4-6"

    @respx.mock
    async def test_complete_returns_assistant_text(self) -> None:
        respx.post(ANTHROPIC_MESSAGES_URL).mock(return_value=_ok_response("salida"))
        llm = AnthropicLLM(api_key="k")
        out = await llm.complete([Message(role="user", content="entrada")])
        assert out == "salida"

    @respx.mock
    async def test_complete_emits_span_with_usage(self) -> None:
        respx.post(ANTHROPIC_MESSAGES_URL).mock(return_value=_ok_response())
        tracer = StubTracer()
        llm = AnthropicLLM(api_key="k", tracer=tracer)
        await llm.complete([Message(role="user", content="hola")])
        assert len(tracer.spans) == 1
        name, span = tracer.spans[0]
        assert name == "llm.complete"
        assert span.attributes.get("gen_ai.system") == "anthropic"
        assert span.attributes.get("gen_ai.request.model") == "claude-sonnet-4-6"
        assert span.attributes.get("gen_ai.usage.input_tokens") == 12
        assert span.attributes.get("gen_ai.usage.output_tokens") == 7
        assert span.attributes.get("gen_ai.usage.cache_read_input_tokens") == 0
        assert span.attributes.get("gen_ai.usage.cache_creation_input_tokens") == 0

    @respx.mock
    async def test_complete_records_non_zero_cache_attribution(self) -> None:
        respx.post(ANTHROPIC_MESSAGES_URL).mock(
            return_value=_ok_response(cache_read=512, cache_creation=128)
        )
        tracer = StubTracer()
        llm = AnthropicLLM(api_key="k", tracer=tracer)
        await llm.complete([Message(role="user", content="hi")])
        _, span = tracer.spans[0]
        assert span.attributes.get("gen_ai.usage.cache_read_input_tokens") == 512
        assert span.attributes.get("gen_ai.usage.cache_creation_input_tokens") == 128

    @respx.mock
    async def test_complete_forwards_cache_control(self) -> None:
        route = respx.post(ANTHROPIC_MESSAGES_URL).mock(return_value=_ok_response())
        llm = AnthropicLLM(api_key="k")
        await llm.complete(
            [
                Message(role="user", content="prefix", cache_control="ephemeral"),
                Message(role="user", content="query"),
            ]
        )
        sent = route.calls.last.request.read()
        assert b'"cache_control"' in sent
        assert b'"ephemeral"' in sent

    @respx.mock
    async def test_complete_system_prompt(self) -> None:
        route = respx.post(ANTHROPIC_MESSAGES_URL).mock(return_value=_ok_response())
        llm = AnthropicLLM(api_key="k")
        await llm.complete(
            [Message(role="user", content="q")],
            system="You are a helpful assistant.",
        )
        sent = route.calls.last.request.read()
        assert b"You are a helpful assistant" in sent

    @respx.mock
    async def test_explicit_system_overrides_role_system_messages(self) -> None:
        route = respx.post(ANTHROPIC_MESSAGES_URL).mock(return_value=_ok_response())
        llm = AnthropicLLM(api_key="k")
        await llm.complete(
            [
                Message(role="system", content="role-system-content"),
                Message(role="user", content="q"),
            ],
            system="explicit-system",
        )
        sent = route.calls.last.request.read()
        assert b"explicit-system" in sent
        assert b"role-system-content" not in sent

    @respx.mock
    async def test_rate_limit_raises_after_retries(self) -> None:
        respx.post(ANTHROPIC_MESSAGES_URL).mock(return_value=httpx.Response(429))
        llm = AnthropicLLM(api_key="k", max_retries=0)
        with pytest.raises(RateLimitError):
            await llm.complete([Message(role="user", content="q")])

    @respx.mock
    async def test_stream_yields_deltas(self) -> None:
        respx.post(ANTHROPIC_MESSAGES_URL).mock(return_value=_sse_stream_response())
        llm = AnthropicLLM(api_key="k")
        out = "".join([c async for c in llm.stream([Message(role="user", content="q")])])
        assert out == "hola mundo"

    @respx.mock
    async def test_stream_emits_span_with_correct_name(self) -> None:
        respx.post(ANTHROPIC_MESSAGES_URL).mock(return_value=_sse_stream_response())
        tracer = StubTracer()
        llm = AnthropicLLM(api_key="k", tracer=tracer)
        async for _ in llm.stream([Message(role="user", content="q")]):
            pass
        assert len(tracer.spans) == 1
        name, span = tracer.spans[0]
        assert name == "llm.stream"
        assert span.attributes.get("gen_ai.system") == "anthropic"
        assert span.attributes.get("gen_ai.request.model") == "claude-sonnet-4-6"

    @respx.mock
    async def test_stream_forwards_cache_control(self) -> None:
        route = respx.post(ANTHROPIC_MESSAGES_URL).mock(return_value=_sse_stream_response())
        llm = AnthropicLLM(api_key="k")
        async for _ in llm.stream(
            [
                Message(role="user", content="prefix", cache_control="ephemeral"),
                Message(role="user", content="query"),
            ]
        ):
            pass
        sent = route.calls.last.request.read()
        assert b'"cache_control"' in sent
        assert b'"ephemeral"' in sent

    @respx.mock
    async def test_complete_authorization_header(self) -> None:
        route = respx.post(ANTHROPIC_MESSAGES_URL).mock(return_value=_ok_response())
        llm = AnthropicLLM(api_key="sk-test-token")
        await llm.complete([Message(role="user", content="q")])
        sent_headers = route.calls.last.request.headers
        assert sent_headers.get("x-api-key") == "sk-test-token"
