# SPDX-License-Identifier: Apache-2.0
"""Reusable test stubs for observability + tracing."""

from __future__ import annotations

from typing import Any


class StubSpanContext:
    """Captures `set_attribute` and `record_exception` calls for assertion."""

    def __init__(self) -> None:
        self.attributes: dict[str, Any] = {}
        self.exceptions: list[BaseException] = []

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def record_exception(self, exception: BaseException) -> None:
        self.exceptions.append(exception)


class StubTracer:
    """Records (name, StubSpanContext) tuples for every span opened."""

    def __init__(self) -> None:
        self.spans: list[tuple[str, StubSpanContext]] = []

    def span(self, name: str, attributes: dict[str, Any] | None = None) -> Any:
        ctx = StubSpanContext()
        if attributes:
            ctx.attributes.update(attributes)
        self.spans.append((name, ctx))
        return _AsyncCtx(ctx)


class _AsyncCtx:
    def __init__(self, ctx: StubSpanContext) -> None:
        self._ctx = ctx

    async def __aenter__(self) -> StubSpanContext:
        return self._ctx

    async def __aexit__(self, *args: object) -> None:
        return None
