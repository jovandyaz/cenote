# SPDX-License-Identifier: Apache-2.0
"""VectorStore Protocol."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol

from cenote.models import Chunk, EmbeddedChunk, RetrievalResult
from cenote.types import Vector


class VectorStore(Protocol):
    """Multi-tenant vector store. `namespace` is mandatory on every method."""

    async def upsert(
        self,
        embedded_chunks: list[EmbeddedChunk],
        namespace: str,
    ) -> None: ...

    async def search(
        self,
        query_vector: Vector,
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]: ...

    async def delete(self, chunk_ids: list[str], namespace: str) -> None: ...

    async def delete_namespace(self, namespace: str) -> None: ...

    def get_all_chunks(
        self,
        namespace: str,
        filter: dict[str, Any] | None = None,
    ) -> AsyncIterator[Chunk]:
        """Yield every chunk in `namespace` (optional metadata exact-match filter).

        Order is implementation-defined but stable for a given namespace.
        Drives BM25Retriever index builds; does not load embeddings.
        """
        ...
