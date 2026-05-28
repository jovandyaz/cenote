# SPDX-License-Identifier: Apache-2.0
"""Pydantic models — the contracts between every cenote module."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Document(BaseModel):
    """Source document before chunking."""

    model_config = ConfigDict(extra="forbid")

    id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str | None = None


class Chunk(BaseModel):
    """Atomic embeddable unit. Produced by a Chunker, consumed by an Embedder."""

    model_config = ConfigDict(extra="forbid")

    id: str
    document_id: str
    content: str
    position: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_hash: str

    @staticmethod
    def make_id(document_id: str, position: int) -> str:
        """Deterministic chunk ID from a document ID and ordinal position."""
        return f"{document_id}:{position}"


class EmbeddedChunk(BaseModel):
    """A Chunk together with its embedding vector and provenance."""

    model_config = ConfigDict(extra="forbid")

    chunk: Chunk
    embedding: list[float]
    embedding_model: str
    dimensions: int


class RetrievalResult(BaseModel):
    """One result returned by a Retriever."""

    model_config = ConfigDict(extra="forbid")

    chunk: Chunk
    score: float
    retriever: str


class Message(BaseModel):
    """Single conversation turn. Anthropic prompt-cache marker is optional.

    `cache_control="ephemeral"` enables Anthropic's default 5-minute cache.
    Longer TTLs (e.g. 1h) are not yet supported; deferred to M1.3 if demand.
    """

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant", "system"]
    content: str
    cache_control: Literal["ephemeral"] | None = None
