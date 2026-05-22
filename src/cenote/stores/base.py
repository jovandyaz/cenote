# SPDX-License-Identifier: Apache-2.0
"""VectorStore Protocol."""

from __future__ import annotations

from typing import Any, Protocol

from cenote.models import EmbeddedChunk, RetrievalResult


class VectorStore(Protocol):
    """Multi-tenant vector store. `namespace` is mandatory on every method."""

    async def upsert(
        self,
        embedded_chunks: list[EmbeddedChunk],
        namespace: str,
    ) -> None: ...

    async def search(
        self,
        query_vector: list[float],
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]: ...

    async def delete(self, chunk_ids: list[str], namespace: str) -> None: ...

    async def delete_namespace(self, namespace: str) -> None: ...
