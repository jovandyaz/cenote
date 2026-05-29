# SPDX-License-Identifier: Apache-2.0
"""Tests for cenote.bench.runner.BenchRunner — orchestrates the 3 retrievers."""

from __future__ import annotations

import pytest

from cenote.bench.miracl import FIXTURE_CORPUS, FIXTURE_QUERIES, MiraclLoader
from cenote.bench.runner import BenchRunner
from cenote.embedders import MockEmbedder
from cenote.stores import InMemoryVectorStore
from cenote.tokenizers import SpanishTokenizer


@pytest.fixture
def loader() -> MiraclLoader:
    return MiraclLoader.from_fixture(
        corpus_path=FIXTURE_CORPUS,
        queries_path=FIXTURE_QUERIES,
    )


@pytest.fixture
def runner(loader: MiraclLoader) -> BenchRunner:
    embedder = MockEmbedder(dimensions=128)
    store = InMemoryVectorStore(dimensions=128)
    return BenchRunner(
        loader=loader,
        embedder=embedder,
        store=store,
        tokenizer=SpanishTokenizer(),
    )


class TestBenchRunner:
    async def test_index_returns_corpus_size(self, runner: BenchRunner) -> None:
        indexed = await runner.index()
        assert indexed == 10

    async def test_index_required_before_run(self, runner: BenchRunner) -> None:
        with pytest.raises(RuntimeError, match="index"):
            await runner.run_all(retrievers=["bm25"])

    async def test_run_bm25_returns_run_dict_per_query(self, runner: BenchRunner) -> None:
        await runner.index()
        runs = await runner.run_all(retrievers=["bm25"], top_k=5)
        assert "bm25" in runs
        assert set(runs["bm25"].keys()) == {"q1", "q2", "q3"}
        for hits in runs["bm25"].values():
            assert len(hits) <= 5

    async def test_run_vector_returns_run_dict_per_query(self, runner: BenchRunner) -> None:
        await runner.index()
        runs = await runner.run_all(retrievers=["vector"], top_k=5)
        assert "vector" in runs
        assert set(runs["vector"].keys()) == {"q1", "q2", "q3"}

    async def test_hybrid_fuses_bm25_and_vector(self, runner: BenchRunner) -> None:
        await runner.index()
        runs = await runner.run_all(retrievers=["bm25", "vector", "hybrid"], top_k=5)
        assert {"bm25", "vector", "hybrid"} <= set(runs.keys())
        assert set(runs["hybrid"].keys()) == {"q1", "q2", "q3"}

    async def test_hybrid_auto_runs_components_when_only_hybrid_requested(
        self, runner: BenchRunner
    ) -> None:
        await runner.index()
        runs = await runner.run_all(retrievers=["hybrid"], top_k=5)
        assert "hybrid" in runs

    async def test_top_k_caps_results_per_query(self, runner: BenchRunner) -> None:
        await runner.index()
        runs = await runner.run_all(retrievers=["vector"], top_k=2)
        for hits in runs["vector"].values():
            assert len(hits) <= 2

    async def test_unknown_retriever_raises(self, runner: BenchRunner) -> None:
        await runner.index()
        with pytest.raises(ValueError, match="unknown"):
            await runner.run_all(retrievers=["nonsense"])
