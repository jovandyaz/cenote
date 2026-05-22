"""Tests for cenote.embedders.mock.MockEmbedder."""

from __future__ import annotations

import hashlib

import pytest

from cenote.embedders import MockEmbedder
from cenote.models import Chunk


def _chunk(text: str, idx: int = 0) -> Chunk:
    return Chunk(
        id=f"d:{idx}",
        document_id="d",
        content=text,
        position=idx,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )


class TestMockEmbedder:
    def test_default_dimensions(self) -> None:
        e = MockEmbedder()
        assert e.dimensions == 1024
        assert e.model_id == "mock:default"

    def test_custom_dimensions(self) -> None:
        e = MockEmbedder(dimensions=128, model_name="tiny")
        assert e.dimensions == 128
        assert e.model_id == "mock:tiny"

    def test_rejects_non_positive_dimensions(self) -> None:
        with pytest.raises(ValueError, match="dimensions must be positive"):
            MockEmbedder(dimensions=0)
        with pytest.raises(ValueError, match="dimensions must be positive"):
            MockEmbedder(dimensions=-1)

    @pytest.mark.asyncio
    async def test_embed_returns_one_vector_per_chunk(self) -> None:
        e = MockEmbedder(dimensions=64)
        chunks = [_chunk("hello", 0), _chunk("world", 1)]
        out = await e.embed(chunks)
        assert len(out) == 2
        for emb, original in zip(out, chunks, strict=True):
            assert emb.chunk == original
            assert len(emb.embedding) == 64
            assert emb.embedding_model == "mock:default"
            assert emb.dimensions == 64

    @pytest.mark.asyncio
    async def test_embeddings_are_deterministic_for_same_content(self) -> None:
        e = MockEmbedder(dimensions=32)
        first = await e.embed([_chunk("same text")])
        second = await e.embed([_chunk("same text")])
        assert first[0].embedding == second[0].embedding

    @pytest.mark.asyncio
    async def test_embeddings_differ_for_different_content(self) -> None:
        e = MockEmbedder(dimensions=32)
        a = await e.embed([_chunk("text A")])
        b = await e.embed([_chunk("text B")])
        assert a[0].embedding != b[0].embedding

    @pytest.mark.asyncio
    async def test_embed_query_returns_vector_of_right_dimensions(self) -> None:
        e = MockEmbedder(dimensions=16)
        v = await e.embed_query("hello world")
        assert len(v) == 16

    @pytest.mark.asyncio
    async def test_query_and_chunk_share_embedding_function(self) -> None:
        e = MockEmbedder(dimensions=16)
        v_query = await e.embed_query("text")
        v_chunk = (await e.embed([_chunk("text")]))[0].embedding
        assert v_query == v_chunk

    @pytest.mark.asyncio
    async def test_embeddings_are_unit_norm(self) -> None:
        """Matches the distribution real embedders produce (concentration of measure)."""
        e = MockEmbedder(dimensions=128)
        out = await e.embed([_chunk("hello"), _chunk("world", 1)])
        for emb in out:
            squared_norm = sum(x * x for x in emb.embedding)
            assert (
                abs(squared_norm - 1.0) < 1e-9
            ), f"vector is not unit-norm: ||v||² = {squared_norm}"
        # Queries too.
        v_q = await e.embed_query("a query")
        assert abs(sum(x * x for x in v_q) - 1.0) < 1e-9
