# SPDX-License-Identifier: Apache-2.0
"""LangfuseTracer — bridges the Tracer Protocol to Langfuse observations."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

try:
    import langfuse as _langfuse  # noqa: F401  (import-time guard for the optional extra)
except ImportError as exc:
    raise ImportError(
        "Langfuse support requires the [langfuse] extra: pip install cenote-core[langfuse]"
    ) from exc

_GEN_AI_ATTR_TO_LANGFUSE_FIELD: dict[str, str] = {
    "gen_ai.request.model": "model",
    "gen_ai.usage.input_tokens": "input_tokens",
    "gen_ai.usage.output_tokens": "output_tokens",
    "gen_ai.usage.cache_read_input_tokens": "cache_read_input_tokens",
    "gen_ai.usage.cache_creation_input_tokens": "cache_creation_input_tokens",
    # gen_ai.system (provider tag) flows through to metadata — Langfuse has no
    # first-class provider field, but metadata indexes for filtering.
}


class LangfuseSpanContext:
    """Bridges Langfuse observation API to the SpanContext Protocol.

    Each `set_attribute` for an unmapped key issues `obs.update(metadata=...)`
    with the cumulative metadata dict; Langfuse SDK deduplicates server-side.
    """

    def __init__(self, observation: Any) -> None:
        self._obs = observation
        self._metadata: dict[str, Any] = {}

    def set_attribute(self, key: str, value: Any) -> None:
        field = _GEN_AI_ATTR_TO_LANGFUSE_FIELD.get(key)
        if field is not None:
            self._obs.update(**{field: value})
        else:
            self._metadata[key] = value
            self._obs.update(metadata=dict(self._metadata))

    def record_exception(self, exception: BaseException) -> None:
        self._obs.update(level="ERROR", status_message=str(exception))


class LangfuseTracer:
    """Adapts a `langfuse.Langfuse` client to the cenote `Tracer` Protocol.

    Spans named with the `llm.` prefix become Langfuse `generation`
    observations (carry model/token metadata); everything else becomes a
    plain `span` observation. The `client` is typed as `Any` because the
    Langfuse SDK surface churns across major versions (v2/v3/v4); we
    duck-type the `generation`/`span` methods rather than pinning a class.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    @asynccontextmanager
    async def span(
        self, name: str, attributes: dict[str, Any] | None = None
    ) -> AsyncIterator[LangfuseSpanContext]:
        kwargs: dict[str, Any] = {"name": name}
        if attributes:
            kwargs["metadata"] = dict(attributes)
        if name.startswith("llm."):
            obs = self._client.generation(**kwargs)
        else:
            obs = self._client.span(**kwargs)
        yield LangfuseSpanContext(obs)


__all__ = ["LangfuseSpanContext", "LangfuseTracer"]
