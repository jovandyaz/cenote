# SPDX-License-Identifier: Apache-2.0
"""Tests for cenote.bench.miracl.MiraclLoader."""

from __future__ import annotations

from pathlib import Path

import pytest

from cenote.bench.miracl import FIXTURE_CORPUS, FIXTURE_QUERIES, MiraclLoader
from cenote.models import Chunk


@pytest.fixture
def loader() -> MiraclLoader:
    return MiraclLoader.from_fixture(
        corpus_path=FIXTURE_CORPUS,
        queries_path=FIXTURE_QUERIES,
    )


class TestMiraclLoaderCorpus:
    async def test_load_corpus_yields_chunks(self, loader: MiraclLoader) -> None:
        chunks = [c async for c in loader.load_corpus()]
        assert len(chunks) == 10
        assert all(isinstance(c, Chunk) for c in chunks)

    async def test_chunk_id_equals_docid(self, loader: MiraclLoader) -> None:
        chunks = [c async for c in loader.load_corpus()]
        first = next(c for c in chunks if c.id == "42#0")
        assert first.document_id == "42#0"

    async def test_content_includes_title_and_text(self, loader: MiraclLoader) -> None:
        chunks = [c async for c in loader.load_corpus()]
        madrid = next(c for c in chunks if c.id == "42#0")
        assert "Madrid" in madrid.content
        assert "capital de España" in madrid.content

    async def test_content_hash_is_deterministic(self, loader: MiraclLoader) -> None:
        first = [c async for c in loader.load_corpus()]
        second = [c async for c in loader.load_corpus()]
        assert [c.content_hash for c in first] == [c.content_hash for c in second]

    async def test_metadata_carries_title_and_source(self, loader: MiraclLoader) -> None:
        chunks = [c async for c in loader.load_corpus()]
        madrid = next(c for c in chunks if c.id == "42#0")
        assert madrid.metadata["title"] == "Madrid"
        assert madrid.metadata["source"] == "miracl-es"


class TestMiraclLoaderQueries:
    async def test_load_queries_returns_dict(self, loader: MiraclLoader) -> None:
        queries = await loader.load_queries()
        assert len(queries) == 3
        assert queries["q1"] == "cuál es la capital de España"
        assert queries["q2"] == "cuántos habitantes tiene Madrid"


class TestMiraclLoaderQrels:
    async def test_load_qrels_binary_relevance(self, loader: MiraclLoader) -> None:
        qrels = await loader.load_qrels()
        assert qrels["q1"] == {"42#0": 1}
        assert qrels["q2"] == {"42#1": 1}

    async def test_multiple_positive_passages_per_query(self, loader: MiraclLoader) -> None:
        qrels = await loader.load_qrels()
        assert qrels["q3"] == {"100#0": 1, "300#0": 1}

    async def test_qrels_only_contains_queries_with_judgments(self, loader: MiraclLoader) -> None:
        qrels = await loader.load_qrels()
        assert set(qrels.keys()) == {"q1", "q2", "q3"}


class TestMiraclLoaderConstruction:
    def test_from_fixture_rejects_missing_corpus(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            MiraclLoader.from_fixture(
                corpus_path=tmp_path / "missing.jsonl",
                queries_path=FIXTURE_QUERIES,
            )

    def test_namespace_is_miracl_language(self, loader: MiraclLoader) -> None:
        assert loader.namespace == "miracl-es"

    def test_from_huggingface_requires_token(self) -> None:
        from cenote.errors import ConfigurationError

        with pytest.raises(ConfigurationError):
            MiraclLoader.from_huggingface(language="es", split="dev", hf_token=None)
