"""Smoke test for the demo script. Runs with MockEmbedder only (no API key needed)."""

from __future__ import annotations

import pytest
from demos.quickstart import run


@pytest.mark.asyncio
async def test_quickstart_runs_with_mock_provider() -> None:
    # Just verify it doesn't raise. Output goes to stdout.
    await run(provider="mock", limit=2)
