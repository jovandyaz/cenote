"""Tests for cenote.chunkers.recursive.RecursiveCharacterChunker."""

from __future__ import annotations

import hashlib

from cenote.chunkers import RecursiveCharacterChunker
from cenote.models import Document


def _sha(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


class TestRecursiveCharacterChunker:
    def test_empty_document_returns_empty_list(self) -> None:
        chunker = RecursiveCharacterChunker()
        doc = Document(id="d", content="")
        assert chunker.chunk(doc) == []

    def test_short_document_returns_single_chunk(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=512, chunk_overlap=50)
        doc = Document(id="d", content="short text")
        chunks = chunker.chunk(doc)
        assert len(chunks) == 1
        assert chunks[0].content == "short text"
        assert chunks[0].position == 0
        assert chunks[0].document_id == "d"
        assert chunks[0].id == "d:0"
        assert chunks[0].content_hash == _sha("short text")

    def test_long_document_splits_into_multiple_chunks(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=10)
        sentence = "This is sentence number {n} of the test document. "
        content = "".join(sentence.format(n=i) for i in range(20))
        chunks = chunker.chunk(Document(id="d", content=content))
        assert len(chunks) > 1
        # Each chunk under (or near) chunk_size, allowing minor overshoot when
        # an atomic token exceeds chunk_size.
        for c in chunks:
            assert len(c.content) <= 100, f"chunk too large: {len(c.content)}"

    def test_positions_are_sequential(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=30, chunk_overlap=5)
        content = "abc " * 50
        chunks = chunker.chunk(Document(id="d", content=content))
        positions = [c.position for c in chunks]
        assert positions == list(range(len(chunks)))

    def test_chunk_ids_use_make_id(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=30, chunk_overlap=5)
        chunks = chunker.chunk(Document(id="doc-99", content="x " * 100))
        for i, c in enumerate(chunks):
            assert c.id == f"doc-99:{i}"

    def test_content_hash_matches_sha256(self) -> None:
        chunker = RecursiveCharacterChunker()
        chunks = chunker.chunk(Document(id="d", content="hello"))
        assert chunks[0].content_hash == _sha("hello")

    def test_metadata_inherited_from_document(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=20, chunk_overlap=2)
        doc = Document(
            id="d",
            content="a " * 50,
            metadata={"author": "alice"},
        )
        chunks = chunker.chunk(doc)
        for c in chunks:
            assert c.metadata == {"author": "alice"}
        # Mutation of source metadata must not leak into chunks
        doc.metadata["author"] = "bob"
        for c in chunks:
            assert c.metadata == {"author": "alice"}

    def test_consecutive_chunks_share_overlap(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=40, chunk_overlap=10)
        content = "a" * 200
        chunks = chunker.chunk(Document(id="d", content=content))
        assert len(chunks) >= 2
        # Tail of chunk[0] should appear at the start of chunk[1]
        tail = chunks[0].content[-10:]
        assert chunks[1].content.startswith(tail)

    def test_unicode_safe(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=30, chunk_overlap=5)
        content = "café — niño — corazón. " * 10
        chunks = chunker.chunk(Document(id="d", content=content))
        # Reconstructed (without overlap dedup) should still contain the unicode
        joined = "".join(c.content for c in chunks)
        assert "café" in joined
        assert "niño" in joined

    def test_zero_overlap_is_supported(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=20, chunk_overlap=0)
        content = "x" * 100
        chunks = chunker.chunk(Document(id="d", content=content))
        # Disjoint reconstruction
        assert "".join(c.content for c in chunks) == content
