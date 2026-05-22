"""Tests for cenote.models."""

from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from cenote.models import Chunk, Document, EmbeddedChunk, RetrievalResult


class TestDocument:
    def test_minimal_construction(self) -> None:
        doc = Document(id="doc-1", content="hello world")
        assert doc.id == "doc-1"
        assert doc.content == "hello world"
        assert doc.metadata == {}
        assert doc.source is None

    def test_with_metadata_and_source(self) -> None:
        doc = Document(
            id="doc-2",
            content="text",
            metadata={"author": "alice", "year": 2026},
            source="https://example.com/doc",
        )
        assert doc.metadata["author"] == "alice"
        assert doc.source == "https://example.com/doc"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            Document(id="d", content="c", unknown_field="x")  # type: ignore[call-arg]


class TestChunk:
    def test_content_hash_matches_sha256(self) -> None:
        content = "the quick brown fox"
        expected = hashlib.sha256(content.encode()).hexdigest()
        chunk = Chunk(
            id="doc-1:0",
            document_id="doc-1",
            content=content,
            position=0,
            content_hash=expected,
        )
        assert chunk.content_hash == expected

    def test_make_id_is_deterministic(self) -> None:
        a = Chunk.make_id("doc-1", 0)
        b = Chunk.make_id("doc-1", 0)
        assert a == b
        assert Chunk.make_id("doc-1", 1) != a

    def test_make_id_format(self) -> None:
        assert Chunk.make_id("doc-1", 0) == "doc-1:0"
        assert Chunk.make_id("doc-1", 42) == "doc-1:42"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            Chunk(  # type: ignore[call-arg]
                id="x",
                document_id="d",
                content="c",
                position=0,
                content_hash="0" * 64,
                bogus="y",
            )


class TestEmbeddedChunk:
    def _make_chunk(self) -> Chunk:
        content = "text"
        return Chunk(
            id="d:0",
            document_id="d",
            content=content,
            position=0,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
        )

    def test_construction(self) -> None:
        chunk = self._make_chunk()
        emb = EmbeddedChunk(
            chunk=chunk,
            embedding=[0.1] * 1024,
            embedding_model="voyage:voyage-3",
            dimensions=1024,
        )
        assert emb.chunk == chunk
        assert len(emb.embedding) == 1024
        assert emb.embedding_model == "voyage:voyage-3"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            EmbeddedChunk(  # type: ignore[call-arg]
                chunk=self._make_chunk(),
                embedding=[0.0],
                embedding_model="m",
                dimensions=1,
                extra="x",
            )


class TestRetrievalResult:
    def test_construction(self) -> None:
        chunk = Chunk(
            id="d:0",
            document_id="d",
            content="c",
            position=0,
            content_hash="0" * 64,
        )
        rr = RetrievalResult(chunk=chunk, score=0.91, retriever="vector")
        assert rr.score == pytest.approx(0.91)
        assert rr.retriever == "vector"

    def test_rejects_extra_fields(self) -> None:
        chunk = Chunk(
            id="d:0",
            document_id="d",
            content="c",
            position=0,
            content_hash="0" * 64,
        )
        with pytest.raises(ValidationError):
            RetrievalResult(  # type: ignore[call-arg]
                chunk=chunk,
                score=1.0,
                retriever="vector",
                bogus=True,
            )


class TestRoundtripSerialization:
    def test_document_roundtrip(self) -> None:
        doc = Document(id="d", content="hello", metadata={"k": 1}, source="s")
        dumped = doc.model_dump()
        restored = Document.model_validate(dumped)
        assert restored == doc

    def test_chunk_roundtrip(self) -> None:
        chunk = Chunk(
            id="d:0",
            document_id="d",
            content="hi",
            position=0,
            content_hash="a" * 64,
            metadata={"section": "intro"},
        )
        restored = Chunk.model_validate(chunk.model_dump())
        assert restored == chunk
