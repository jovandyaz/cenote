# SPDX-License-Identifier: Apache-2.0
"""Test factories — shared Chunk/EmbeddedChunk/RetrievalResult builders."""

from __future__ import annotations

import hashlib

from cenote.models import Chunk, EmbeddedChunk, RetrievalResult


def make_chunk(content: str, *, idx: int = 0, document_id: str = "d") -> Chunk:
    """Build a Chunk with deterministic id/content_hash from the content."""
    return Chunk(
        id=f"{document_id}:{idx}",
        document_id=document_id,
        content=content,
        position=idx,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )


def make_embedded(
    content: str,
    vector: list[float],
    *,
    idx: int = 0,
    document_id: str = "d",
    model: str = "mock:default",
) -> EmbeddedChunk:
    """Build an EmbeddedChunk wrapping a make_chunk-style Chunk."""
    return EmbeddedChunk(
        chunk=make_chunk(content, idx=idx, document_id=document_id),
        embedding=vector,
        embedding_model=model,
        dimensions=len(vector),
    )


def make_result(
    content: str,
    score: float,
    *,
    idx: int = 0,
    retriever: str = "vector",
    document_id: str = "d",
) -> RetrievalResult:
    """Build a RetrievalResult with a deterministic Chunk inside."""
    return RetrievalResult(
        chunk=make_chunk(content, idx=idx, document_id=document_id),
        score=score,
        retriever=retriever,
    )
