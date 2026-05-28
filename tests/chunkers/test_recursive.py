"""Tests for cenote.chunkers.recursive.RecursiveCharacterChunker."""

from __future__ import annotations

import hashlib

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

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


@given(
    content=st.text(min_size=1, max_size=2000),
    chunk_size=st.integers(min_value=32, max_value=512),
    overlap=st.integers(min_value=0, max_value=31),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100)
def test_chunks_never_exceed_chunk_size(content: str, chunk_size: int, overlap: int) -> None:
    """Every produced chunk's content length must be <= chunk_size."""
    chunker = RecursiveCharacterChunker(chunk_size=chunk_size, chunk_overlap=overlap)
    doc = Document(id="d", content=content)
    chunks = chunker.chunk(doc)
    for c in chunks:
        assert len(c.content) <= chunk_size, f"chunk {c.id} has {len(c.content)} > {chunk_size}"


@given(content=st.text(min_size=1, max_size=2000))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
def test_chunks_preserve_full_content_with_zero_overlap(content: str) -> None:
    """With overlap=0, concatenated chunks must equal the original content."""
    chunker = RecursiveCharacterChunker(chunk_size=256, chunk_overlap=0)
    doc = Document(id="d", content=content)
    chunks = chunker.chunk(doc)
    if not chunks:
        assert not content
        return
    reconstructed = "".join(c.content for c in chunks)
    assert reconstructed == content


@given(
    content=st.text(min_size=10, max_size=2000),
    chunk_size=st.integers(min_value=64, max_value=512),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
def test_chunk_ids_are_unique(content: str, chunk_size: int) -> None:
    """All chunk IDs in a single document's output must be unique."""
    chunker = RecursiveCharacterChunker(chunk_size=chunk_size, chunk_overlap=0)
    doc = Document(id="d", content=content)
    chunks = chunker.chunk(doc)
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))
