# SPDX-License-Identifier: Apache-2.0
"""AnthropicLLM — Claude with prompt caching via the official anthropic SDK."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any, cast

from anthropic import APIStatusError, AsyncAnthropic
from anthropic import RateLimitError as _AnthropicRateLimitError
from anthropic.types import MessageParam

from cenote.embedders._http import RateLimiter
from cenote.errors import ConfigurationError, LLMError, RateLimitError
from cenote.models import Message
from cenote.observability.base import NoopTracer, SpanContext, Tracer

logger = logging.getLogger(__name__)


class AnthropicLLM:
    """Anthropic Claude client with prompt caching + tracing.

    `cache_control="ephemeral"` on a Message inserts the Anthropic cache
    marker. Spans are emitted as `llm.complete` / `llm.stream` with
    `gen_ai.*` attributes (model, input/output tokens, cache hit/miss).
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        *,
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        requests_per_minute: int | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        if not api_key:
            raise ConfigurationError("api_key is required")
        if max_retries < 0:
            raise ConfigurationError("max_retries must be non-negative")
        self._model = model
        self._client = AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._tracer = tracer if tracer is not None else NoopTracer()
        self._rate_limiter = RateLimiter(requests_per_minute) if requests_per_minute else None

    @property
    def model_id(self) -> str:
        return f"anthropic:{self._model}"

    def _to_anthropic_messages(self, messages: list[Message]) -> list[MessageParam]:
        out: list[MessageParam] = []
        for m in messages:
            if m.role == "system":
                continue
            content: list[dict[str, Any]] | str
            if m.cache_control == "ephemeral":
                content = [
                    {
                        "type": "text",
                        "text": m.content,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            else:
                content = m.content
            out.append(cast(MessageParam, {"role": m.role, "content": content}))
        return out

    @staticmethod
    def _system_from(messages: list[Message], explicit: str | None) -> str | None:
        if explicit is not None:
            return explicit
        sys_msgs = [m.content for m in messages if m.role == "system"]
        return "\n\n".join(sys_msgs) if sys_msgs else None

    def _build_kwargs(
        self,
        messages: list[Message],
        max_tokens: int,
        temperature: float,
        system: str | None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": self._to_anthropic_messages(messages),
        }
        resolved_system = self._system_from(messages, system)
        if resolved_system is not None:
            kwargs["system"] = resolved_system
        return kwargs

    @staticmethod
    def _record_usage(span: SpanContext, usage: Any) -> None:
        """Attach token-usage attributes to the span.

        Cache fields can be `None` when caching isn't engaged on a given call;
        coerce to 0 so span attribute types stay stable across calls.
        """
        span.set_attribute("gen_ai.usage.input_tokens", usage.input_tokens)
        span.set_attribute("gen_ai.usage.output_tokens", usage.output_tokens)
        span.set_attribute(
            "gen_ai.usage.cache_read_input_tokens",
            getattr(usage, "cache_read_input_tokens", 0) or 0,
        )
        span.set_attribute(
            "gen_ai.usage.cache_creation_input_tokens",
            getattr(usage, "cache_creation_input_tokens", 0) or 0,
        )

    @staticmethod
    def _map_anthropic_error(exc: Exception) -> RateLimitError | LLMError:
        if isinstance(exc, _AnthropicRateLimitError):
            return RateLimitError(str(exc))
        return LLMError(str(exc))

    async def complete(
        self,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: str | None = None,
    ) -> str:
        """Return the assistant text for a single turn.

        Precedence: if `system` is passed AND any `Message(role="system", ...)`
        appears in `messages`, the explicit `system` kwarg wins and the
        role-system messages are dropped from the API payload.
        """
        async with self._tracer.span("llm.complete") as span:
            span.set_attribute("gen_ai.system", "anthropic")
            span.set_attribute("gen_ai.request.model", self._model)
            try:
                if self._rate_limiter is not None:
                    async with self._rate_limiter:
                        response = await self._client.messages.create(
                            **self._build_kwargs(messages, max_tokens, temperature, system)
                        )
                else:
                    response = await self._client.messages.create(
                        **self._build_kwargs(messages, max_tokens, temperature, system)
                    )
            except (_AnthropicRateLimitError, APIStatusError) as exc:
                mapped = self._map_anthropic_error(exc)
                span.record_exception(mapped)
                raise mapped from exc
            self._record_usage(span, response.usage)
            return "".join(block.text for block in response.content if block.type == "text")

    async def stream(
        self,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield assistant text deltas as they arrive from the model.

        Precedence: same as `complete()` — explicit `system` kwarg wins
        over role-system entries in `messages`.
        """
        async with self._tracer.span("llm.stream") as span:
            span.set_attribute("gen_ai.system", "anthropic")
            span.set_attribute("gen_ai.request.model", self._model)
            try:
                kwargs = self._build_kwargs(messages, max_tokens, temperature, system)
                async with self._client.messages.stream(**kwargs) as stream:
                    async for text in stream.text_stream:
                        yield text
                    final = await stream.get_final_message()
                    self._record_usage(span, final.usage)
            except (_AnthropicRateLimitError, APIStatusError) as exc:
                mapped = self._map_anthropic_error(exc)
                span.record_exception(mapped)
                raise mapped from exc
