# SPDX-License-Identifier: Apache-2.0
"""Chunker Protocol."""

from __future__ import annotations

from typing import Protocol

from cenote.models import Chunk, Document


class Chunker(Protocol):
    """Splits a Document into a list of Chunks.

    Contract — `chunk.content` is the exact text that will be embedded.

    Implementations that prepend contextual information (e.g. heading hierarchy
    in a MarkdownChunker, code-block fences in a CodeChunker) MUST include that
    context in `chunk.content`, not only in `chunk.metadata`. The embedding
    cache keys off `(model_id, sha256(chunk.content))`; two chunks with the
    same body but different context would collide and return the wrong vector.

    The companion `chunk.content_hash` is `sha256(chunk.content)` and is set
    by the implementation. Callers must not mutate `chunk.content` after the
    chunker returns.
    """

    def chunk(self, document: Document) -> list[Chunk]:
        """Return the document split into ordered Chunks."""
        ...
