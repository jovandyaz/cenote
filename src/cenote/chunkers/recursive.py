# SPDX-License-Identifier: Apache-2.0
"""RecursiveCharacterChunker — splits text by a priority list of separators."""

from __future__ import annotations

import hashlib
from copy import deepcopy

from cenote.models import Chunk, Document

DEFAULT_SEPARATORS: tuple[str, ...] = ("\n\n", "\n", ". ", " ", "")


class RecursiveCharacterChunker:
    """Recursively splits a Document using separators in priority order.

    Algorithm:
    1. Try to split the text on the highest-priority separator.
    2. For each resulting piece, if it fits under `chunk_size`, keep it.
    3. Otherwise, recurse on it with the next separator.
    4. After all pieces fit, glue adjacent pieces back together up to
       `chunk_size`, producing the final chunk list with `chunk_overlap`
       characters of overlap between consecutive chunks.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: tuple[str, ...] = DEFAULT_SEPARATORS,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be in [0, chunk_size)")
        if not separators:
            raise ValueError("separators must be non-empty")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators

    def chunk(self, document: Document) -> list[Chunk]:
        """Return the document split into ordered Chunks."""
        if not document.content:
            return []
        pieces = self._split_text(document.content, list(self.separators))
        glued = self._glue(pieces)
        return [
            Chunk(
                id=Chunk.make_id(document.id, i),
                document_id=document.id,
                content=text,
                position=i,
                metadata=deepcopy(document.metadata),
                content_hash=hashlib.sha256(text.encode()).hexdigest(),
            )
            for i, text in enumerate(glued)
        ]

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]
        if not separators:
            # Fall back to hard slice — keeps pieces under chunk_size.
            return [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]
        sep = separators[0]
        remaining = separators[1:]
        if sep == "":
            return self._split_text(text, remaining)
        parts = text.split(sep)
        result: list[str] = []
        for idx, part in enumerate(parts):
            piece = part + (sep if idx < len(parts) - 1 else "")
            if len(piece) <= self.chunk_size:
                result.append(piece)
            else:
                result.extend(self._split_text(piece, remaining))
        return [p for p in result if p]

    def _glue(self, pieces: list[str]) -> list[str]:
        if not pieces:
            return []
        chunks: list[str] = []
        current = ""
        for piece in pieces:
            if not current:
                current = piece
                continue
            if len(current) + len(piece) <= self.chunk_size:
                current += piece
            else:
                chunks.append(current)
                tail = current[-self.chunk_overlap :] if self.chunk_overlap else ""
                current = tail + piece
        if current:
            chunks.append(current)
        return chunks
