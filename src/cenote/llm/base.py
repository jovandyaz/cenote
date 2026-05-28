# SPDX-License-Identifier: Apache-2.0
"""LLMClient Protocol + NoopLLM default."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from cenote.models import Message


class LLMClient(Protocol):
    """Async LLM client. Implementations expose a stable model_id + complete/stream."""

    @property
    def model_id(self) -> str:
        """'provider:model_name', e.g. 'anthropic:claude-sonnet-4-6'."""
        ...

    async def complete(
        self,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: str | None = None,
    ) -> str:
        """Return the assistant text for a single message turn."""
        ...

    async def stream(
        self,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield assistant text deltas as they arrive from the model."""
        ...


class NoopLLM:
    """LLMClient that returns empty output. For tests that don't need real LLM calls."""

    @property
    def model_id(self) -> str:
        return "noop:noop"

    async def complete(
        self,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: str | None = None,
    ) -> str:
        return ""

    async def stream(
        self,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: str | None = None,
    ) -> AsyncIterator[str]:
        return
        yield  # pragma: no cover
