# SPDX-License-Identifier: Apache-2.0
"""Embedder Protocol."""

from __future__ import annotations

from typing import Protocol

from cenote.models import Chunk, EmbeddedChunk


class Embedder(Protocol):
    """Embeds chunks and queries. `embed(chunks)` must preserve input order."""

    @property
    def model_id(self) -> str:
        """`'provider:model_name'`, e.g. `'voyage:voyage-3'`."""
        ...

    @property
    def dimensions(self) -> int: ...

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]: ...

    async def embed_query(self, query: str) -> list[float]: ...
