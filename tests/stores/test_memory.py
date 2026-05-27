"""Tests for InMemoryVectorStore."""

from __future__ import annotations

import hashlib

import pytest

from cenote.errors import ConfigurationError, DimensionMismatchError
from cenote.models import Chunk, EmbeddedChunk
from cenote.stores import InMemoryVectorStore


def _embedded(
    text: str, vector: list[float], *, idx: int = 0, namespace_doc_id: str = "d"
) -> EmbeddedChunk:
    chunk = Chunk(
        id=f"{namespace_doc_id}:{idx}",
        document_id=namespace_doc_id,
        content=text,
        position=idx,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    return EmbeddedChunk(
        chunk=chunk,
        embedding=vector,
        embedding_model="mock:default",
        dimensions=len(vector),
    )


@pytest.mark.asyncio
class TestInMemoryVectorStore:
    async def test_search_empty_returns_empty(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        out = await store.search([0.0] * 4, namespace="ns")
        assert out == []

    async def test_roundtrip_upsert_and_search(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        items = [
            _embedded("hello", [1.0, 0.0, 0.0, 0.0], idx=0),
            _embedded("world", [0.0, 1.0, 0.0, 0.0], idx=1),
            _embedded("foo", [0.0, 0.0, 1.0, 0.0], idx=2),
        ]
        await store.upsert(items, namespace="ns")
        out = await store.search([1.0, 0.0, 0.0, 0.0], namespace="ns", limit=2)
        assert len(out) == 2
        assert out[0].chunk.content == "hello"
        assert out[0].retriever == "vector"
        assert out[0].score > out[1].score

    async def test_namespace_isolation(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        await store.upsert([_embedded("only-a", [1.0, 0.0, 0.0, 0.0])], namespace="A")
        await store.upsert([_embedded("only-b", [1.0, 0.0, 0.0, 0.0])], namespace="B")
        out_a = await store.search([1.0, 0.0, 0.0, 0.0], namespace="A")
        out_b = await store.search([1.0, 0.0, 0.0, 0.0], namespace="B")
        contents_a = [r.chunk.content for r in out_a]
        contents_b = [r.chunk.content for r in out_b]
        assert "only-a" in contents_a and "only-b" not in contents_a
        assert "only-b" in contents_b and "only-a" not in contents_b

    async def test_metadata_filter(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        a = _embedded("alpha", [1.0, 0.0, 0.0, 0.0], idx=0)
        b = _embedded("beta", [1.0, 0.0, 0.0, 0.0], idx=1)
        # Construct chunks with metadata
        a.chunk.metadata["lang"] = "en"
        b.chunk.metadata["lang"] = "es"
        await store.upsert([a, b], namespace="ns")
        out_es = await store.search([1.0, 0.0, 0.0, 0.0], namespace="ns", filter={"lang": "es"})
        assert {r.chunk.content for r in out_es} == {"beta"}

    async def test_delete_single_chunk(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        a = _embedded("alpha", [1.0, 0.0, 0.0, 0.0], idx=0)
        b = _embedded("beta", [0.0, 1.0, 0.0, 0.0], idx=1)
        await store.upsert([a, b], namespace="ns")
        await store.delete([a.chunk.id], namespace="ns")
        out = await store.search([1.0, 0.0, 0.0, 0.0], namespace="ns")
        assert "alpha" not in {r.chunk.content for r in out}

    async def test_delete_namespace(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        await store.upsert([_embedded("a", [1.0, 0.0, 0.0, 0.0])], namespace="ns")
        await store.delete_namespace("ns")
        out = await store.search([1.0, 0.0, 0.0, 0.0], namespace="ns")
        assert out == []

    async def test_upsert_overwrites_existing_id(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        v0 = _embedded("first", [1.0, 0.0, 0.0, 0.0], idx=0)
        await store.upsert([v0], namespace="ns")
        # Same id, different content and vector.
        v0_new = EmbeddedChunk(
            chunk=Chunk(
                id=v0.chunk.id,
                document_id=v0.chunk.document_id,
                content="updated",
                position=0,
                content_hash=hashlib.sha256(b"updated").hexdigest(),
            ),
            embedding=[0.0, 1.0, 0.0, 0.0],
            embedding_model=v0.embedding_model,
            dimensions=v0.dimensions,
        )
        await store.upsert([v0_new], namespace="ns")
        out = await store.search([0.0, 1.0, 0.0, 0.0], namespace="ns", limit=5)
        assert out[0].chunk.content == "updated"

    async def test_dimension_mismatch_raises(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        with pytest.raises(DimensionMismatchError):
            await store.upsert([_embedded("x", [1.0, 0.0])], namespace="ns")
        with pytest.raises(DimensionMismatchError):
            await store.search([1.0, 0.0], namespace="ns")

    async def test_zero_norm_query_returns_empty(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        await store.upsert([_embedded("x", [1.0, 0.0, 0.0, 0.0])], namespace="ns")
        out = await store.search([0.0, 0.0, 0.0, 0.0], namespace="ns")
        assert out == []

    async def test_zero_norm_vector_skipped_in_search(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        await store.upsert([_embedded("zero", [0.0, 0.0, 0.0, 0.0])], namespace="ns")
        out = await store.search([1.0, 0.0, 0.0, 0.0], namespace="ns")
        assert out == []

    async def test_delete_nonexistent_namespace_noop(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        # Must not raise when namespace bucket does not exist.
        await store.delete(["d:0"], namespace="missing")


def test_invalid_dimensions_raises() -> None:
    with pytest.raises(ConfigurationError):
        InMemoryVectorStore(dimensions=0)


@pytest.mark.asyncio
class TestInMemoryGetAllChunks:
    async def test_yields_every_chunk_in_namespace(self) -> None:
        store = InMemoryVectorStore(dimensions=2)
        items = [_embedded("a", [1.0, 0.0], idx=0), _embedded("b", [0.0, 1.0], idx=1)]
        await store.upsert(items, namespace="ns")

        out: list[Chunk] = []
        async for c in store.get_all_chunks(namespace="ns"):
            out.append(c)
        assert {c.content for c in out} == {"a", "b"}

    async def test_namespace_isolation(self) -> None:
        store = InMemoryVectorStore(dimensions=2)
        await store.upsert([_embedded("a", [1.0, 0.0])], namespace="ns-a")
        await store.upsert([_embedded("b", [0.0, 1.0])], namespace="ns-b")
        a_out = [c async for c in store.get_all_chunks(namespace="ns-a")]
        assert {c.content for c in a_out} == {"a"}

    async def test_missing_namespace_yields_nothing(self) -> None:
        store = InMemoryVectorStore(dimensions=2)
        assert [c async for c in store.get_all_chunks(namespace="missing")] == []

    async def test_filter_metadata(self) -> None:
        store = InMemoryVectorStore(dimensions=2)
        a = _embedded("a", [1.0, 0.0], idx=0)
        b = _embedded("b", [0.0, 1.0], idx=1)
        a.chunk.metadata["lang"] = "en"
        b.chunk.metadata["lang"] = "es"
        await store.upsert([a, b], namespace="ns")
        out = [c async for c in store.get_all_chunks(namespace="ns", filter={"lang": "es"})]
        assert [c.content for c in out] == ["b"]
