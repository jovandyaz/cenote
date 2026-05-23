"""NoopTracer must be a valid no-op context manager."""

from __future__ import annotations

import pytest

from cenote.observability import NoopTracer


@pytest.mark.asyncio
async def test_noop_tracer_yields_without_error() -> None:
    tracer = NoopTracer()
    async with tracer.span("test", {"k": "v"}):
        pass  # no exception is the assertion
