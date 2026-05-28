# SPDX-License-Identifier: Apache-2.0
"""Performance benchmarks for SqliteCache batch writes (WAL + synchronous=NORMAL claim)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from cenote.embedders.cache import SqliteCache


@pytest.mark.benchmark
def test_sqlite_set_many_1000_vectors_1024d(benchmark, tmp_path: Path) -> None:
    """Bulk write 1000 vectors of dim 1024 in a single transaction."""
    items = [
        ("voyage:voyage-3", f"hash{i}", [float(j) * 0.001 for j in range(1024)])
        for i in range(1000)
    ]

    def _run() -> None:
        async def _inner() -> None:
            cache = await SqliteCache.connect(tmp_path / f"bench_{id(items)}.db")
            try:
                await cache.set_many(items)
            finally:
                await cache.close()

        asyncio.run(_inner())

    benchmark(_run)
