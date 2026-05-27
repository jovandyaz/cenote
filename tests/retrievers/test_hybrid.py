# SPDX-License-Identifier: Apache-2.0
"""Tests for HybridRetriever — Reciprocal Rank Fusion."""

from __future__ import annotations

from typing import Any

import pytest

from cenote.errors import ConfigurationError
from cenote.models import RetrievalResult
from cenote.retrievers import HybridRetriever
from tests._factories import make_result


class _StubRetriever:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self._results = results

    async def retrieve(
        self,
        query: str,
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        return list(self._results[:limit])


@pytest.mark.asyncio
class TestHybridRetriever:
    async def test_chunk_in_only_one_retriever_still_appears(self) -> None:
        v = _StubRetriever([make_result("alpha", 0.9, idx=0, retriever="vector")])
        b = _StubRetriever([make_result("beta", 0.8, idx=1, retriever="bm25")])
        retriever = HybridRetriever([v, b])
        out = await retriever.retrieve("q", namespace="ns", limit=5)
        assert {r.chunk.content for r in out} == {"alpha", "beta"}

    async def test_chunk_in_both_retrievers_outranks_single(self) -> None:
        common = make_result("common", 0.5, idx=0)
        v = _StubRetriever([common, make_result("only-v", 0.5, idx=1)])
        b = _StubRetriever([common, make_result("only-b", 0.5, idx=2)])
        retriever = HybridRetriever([v, b])
        out = await retriever.retrieve("q", namespace="ns", limit=10)
        assert out[0].chunk.content == "common"
        assert out[0].retriever == "hybrid"

    async def test_weights_change_ranking(self) -> None:
        v = _StubRetriever([make_result("a-top", 0.9, idx=0), make_result("a-bot", 0.1, idx=1)])
        b = _StubRetriever([make_result("b-top", 0.9, idx=2), make_result("b-bot", 0.1, idx=3)])
        retriever = HybridRetriever([v, b], weights=[10.0, 1.0])
        out = await retriever.retrieve("q", namespace="ns", limit=4)
        assert out[0].chunk.content == "a-top"

    async def test_namespace_passed_through(self) -> None:
        captured: dict[str, str] = {}

        class _Cap(_StubRetriever):
            async def retrieve(
                self, query: str, namespace: str, **kw: Any
            ) -> list[RetrievalResult]:
                captured["ns"] = namespace
                return await super().retrieve(query, namespace, **kw)

        retriever = HybridRetriever([_Cap([make_result("x", 0.5)])])
        await retriever.retrieve("q", namespace="my-ns", limit=1)
        assert captured["ns"] == "my-ns"

    async def test_empty_corpus_returns_empty(self) -> None:
        retriever = HybridRetriever([_StubRetriever([]), _StubRetriever([])])
        out = await retriever.retrieve("q", namespace="ns", limit=5)
        assert out == []

    async def test_limit_respected(self) -> None:
        items = [make_result(f"t{i}", 0.5, idx=i) for i in range(20)]
        v = _StubRetriever(items)
        retriever = HybridRetriever([v])
        out = await retriever.retrieve("q", namespace="ns", limit=3)
        assert len(out) == 3

    async def test_three_retrievers_supported(self) -> None:
        v = _StubRetriever([make_result("v", 0.9, idx=0)])
        b = _StubRetriever([make_result("b", 0.9, idx=1)])
        h = _StubRetriever([make_result("h", 0.9, idx=2)])
        retriever = HybridRetriever([v, b, h])
        out = await retriever.retrieve("q", namespace="ns", limit=5)
        assert {r.chunk.content for r in out} == {"v", "b", "h"}

    async def test_weights_must_match_retrievers(self) -> None:
        with pytest.raises(ConfigurationError):
            HybridRetriever([_StubRetriever([])], weights=[1.0, 2.0])

    async def test_invalid_k_constant_raises(self) -> None:
        with pytest.raises(ConfigurationError):
            HybridRetriever([_StubRetriever([])], k_constant=0)

    async def test_invalid_candidate_pool_size_raises(self) -> None:
        with pytest.raises(ConfigurationError):
            HybridRetriever([_StubRetriever([])], candidate_pool_size=0)

    async def test_k_constant_changes_score_magnitudes(self) -> None:
        items = [make_result(f"t{i}", 0.5, idx=i) for i in range(3)]
        small_k = await HybridRetriever([_StubRetriever(items)], k_constant=1).retrieve(
            "q", namespace="ns", limit=3
        )
        large_k = await HybridRetriever([_StubRetriever(items)], k_constant=1000).retrieve(
            "q", namespace="ns", limit=3
        )
        assert small_k[0].score > large_k[0].score
        assert [c.chunk.content for c in small_k] == [c.chunk.content for c in large_k]

    async def test_score_ties_resolved_by_first_seen_order(self) -> None:
        a = make_result("a", 0.5, idx=0)
        b = make_result("b", 0.5, idx=1)
        out = await HybridRetriever([_StubRetriever([a, b]), _StubRetriever([a, b])]).retrieve(
            "q", namespace="ns", limit=2
        )
        assert [r.chunk.content for r in out] == ["a", "b"]

    async def test_candidate_pool_size_passed_through(self) -> None:
        captured: list[int] = []

        class _Cap(_StubRetriever):
            async def retrieve(
                self,
                query: str,
                namespace: str,
                limit: int = 10,
                filter: dict[str, Any] | None = None,
            ) -> list[RetrievalResult]:
                captured.append(limit)
                return []

        await HybridRetriever([_Cap([])], candidate_pool_size=500).retrieve(
            "q", namespace="ns", limit=5
        )
        assert captured == [500]

    async def test_candidate_pool_default_uses_heuristic(self) -> None:
        captured: list[int] = []

        class _Cap(_StubRetriever):
            async def retrieve(
                self,
                query: str,
                namespace: str,
                limit: int = 10,
                filter: dict[str, Any] | None = None,
            ) -> list[RetrievalResult]:
                captured.append(limit)
                return []

        await HybridRetriever([_Cap([])]).retrieve("q", namespace="ns", limit=5)
        assert captured == [100]  # max(5 * 4, 100) == 100
        captured.clear()
        await HybridRetriever([_Cap([])]).retrieve("q", namespace="ns", limit=50)
        assert captured == [200]  # max(50 * 4, 100) == 200
