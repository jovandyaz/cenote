# SPDX-License-Identifier: Apache-2.0
"""Tests for LLMClient Protocol + NoopLLM + Message model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cenote.errors import CenoteError, LLMError
from cenote.llm import LLMClient, NoopLLM
from cenote.models import Message


class TestMessageModel:
    def test_valid_user_message(self) -> None:
        m = Message(role="user", content="hola")
        assert m.role == "user"
        assert m.content == "hola"
        assert m.cache_control is None

    def test_cache_control_ephemeral(self) -> None:
        m = Message(role="user", content="x", cache_control="ephemeral")
        assert m.cache_control == "ephemeral"

    def test_invalid_role_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Message(role="bot", content="x")  # type: ignore[arg-type]

    def test_invalid_cache_control_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Message(role="user", content="x", cache_control="permanent")  # type: ignore[arg-type]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            Message(role="user", content="x", extra="oops")  # type: ignore[call-arg]


class TestLLMError:
    def test_subclass_of_cenote_error(self) -> None:
        assert issubclass(LLMError, CenoteError)


@pytest.mark.asyncio
class TestNoopLLM:
    async def test_satisfies_protocol(self) -> None:
        llm: LLMClient = NoopLLM()
        assert callable(llm.complete)
        assert callable(llm.stream)

    async def test_model_id(self) -> None:
        assert NoopLLM().model_id == "noop:noop"

    async def test_complete_returns_empty(self) -> None:
        out = await NoopLLM().complete([Message(role="user", content="hi")])
        assert out == ""

    async def test_stream_yields_nothing(self) -> None:
        chunks = [c async for c in NoopLLM().stream([Message(role="user", content="hi")])]
        assert chunks == []
