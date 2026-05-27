# SPDX-License-Identifier: Apache-2.0
"""Tests for RetrievalBenchmark."""

from __future__ import annotations

from typing import Any

import pytest

from cenote.errors import ConfigurationError
from cenote.eval import (
    BenchmarkResult,
    EvalDataset,
    Query,
    RetrievalBenchmark,
)
from cenote.models import Document, RetrievalResult
from tests._factories import make_result


class _StubRetriever:
    """Returns a hard-coded ranked list per query for deterministic eval tests."""

    def __init__(self, ranked: dict[str, list[str]]) -> None:
        self._ranked = ranked

    async def retrieve(
        self,
        query: str,
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        ids = self._ranked.get(query, [])
        return [
            make_result(f"content for {did}", score=1.0 / (i + 1), document_id=did)
            for i, did in enumerate(ids[:limit])
        ]


class _StubRetrieverWithModel(_StubRetriever):
    model_id = "voyage:rerank-2"


def _small_dataset() -> EvalDataset:
    docs = [Document(id=f"d{i}", content=f"text {i}") for i in range(5)]
    queries = [
        Query(id="q1", text="query 1", relevant_doc_ids=("d0", "d1")),
        Query(id="q2", text="query 2", relevant_doc_ids=("d2",)),
    ]
    return EvalDataset(name="tiny", language="en", documents=docs, queries=queries)


@pytest.mark.asyncio
class TestRetrievalBenchmark:
    async def test_perfect_retriever_scores_one(self) -> None:
        retriever = _StubRetriever({"query 1": ["d0", "d1"], "query 2": ["d2"]})
        bench = RetrievalBenchmark(retriever=retriever, namespace="ns")
        result = await bench.run(_small_dataset(), k=2)
        assert isinstance(result, BenchmarkResult)
        assert result.precision_at_k == pytest.approx(1.0)
        assert result.recall_at_k == pytest.approx(1.0)
        assert result.mrr == pytest.approx(1.0)

    async def test_zero_retriever_scores_zero(self) -> None:
        retriever = _StubRetriever({"query 1": ["d4"], "query 2": ["d4"]})
        bench = RetrievalBenchmark(retriever=retriever, namespace="ns")
        result = await bench.run(_small_dataset(), k=2)
        assert result.precision_at_k == 0.0
        assert result.recall_at_k == 0.0
        assert result.mrr == 0.0

    async def test_per_query_results_included(self) -> None:
        retriever = _StubRetriever({"query 1": ["d0"], "query 2": ["d2"]})
        bench = RetrievalBenchmark(retriever=retriever, namespace="ns")
        result = await bench.run(_small_dataset(), k=5)
        assert set(result.per_query) == {"q1", "q2"}
        assert result.per_query["q2"]["precision_at_k"] == pytest.approx(1.0)
        assert result.per_query["q2"]["recall_at_k"] == pytest.approx(1.0)
        assert result.per_query["q2"]["mrr"] == pytest.approx(1.0)
        assert result.per_query["q1"]["precision_at_k"] == pytest.approx(1.0)
        assert result.per_query["q1"]["recall_at_k"] == pytest.approx(0.5)

    async def test_dataset_name_recorded(self) -> None:
        retriever = _StubRetriever({"query 1": [], "query 2": []})
        bench = RetrievalBenchmark(retriever=retriever, namespace="ns")
        result = await bench.run(_small_dataset(), k=3)
        assert result.dataset == "tiny"

    async def test_retriever_label_without_model_id(self) -> None:
        bench = RetrievalBenchmark(retriever=_StubRetriever({}))
        result = await bench.run(_small_dataset(), k=2)
        assert result.retriever_label == "_StubRetriever"

    async def test_retriever_label_includes_model_id_when_available(self) -> None:
        bench = RetrievalBenchmark(retriever=_StubRetrieverWithModel({}))
        result = await bench.run(_small_dataset(), k=2)
        assert "voyage:rerank-2" in result.retriever_label
        assert "_StubRetrieverWithModel" in result.retriever_label

    async def test_empty_queries_returns_zero_metrics(self) -> None:
        ds = EvalDataset(name="empty", language="en", documents=[], queries=[])
        result = await RetrievalBenchmark(_StubRetriever({})).run(ds, k=3)
        assert result.precision_at_k == 0.0
        assert result.recall_at_k == 0.0
        assert result.mrr == 0.0
        assert result.per_query == {}

    async def test_k_zero_propagates_configuration_error(self) -> None:
        retriever = _StubRetriever({"query 1": ["d0"], "query 2": ["d2"]})
        with pytest.raises(ConfigurationError):
            await RetrievalBenchmark(retriever=retriever).run(_small_dataset(), k=0)

    async def test_qrels_derived_from_queries(self) -> None:
        ds = _small_dataset()
        assert ds.qrels == {"q1": {"d0", "d1"}, "q2": {"d2"}}
