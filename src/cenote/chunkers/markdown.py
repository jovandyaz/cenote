# SPDX-License-Identifier: Apache-2.0
"""MarkdownChunker — structure-aware splitter respecting headings, code, lists."""

from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Callable
from copy import deepcopy

from cenote.chunkers.recursive import RecursiveCharacterChunker
from cenote.errors import ConfigurationError
from cenote.models import Chunk, Document

logger = logging.getLogger(__name__)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_FENCE_RE = re.compile(r"^(```|~~~)")
_TABLE_ROW_RE = re.compile(r"^\s*\|.+\|\s*$")
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")
_BLOCKQUOTE_RE = re.compile(r"^\s*>")


def _is_table_row(line: str) -> bool:
    return _TABLE_ROW_RE.match(line) is not None


def _is_blockquote(line: str) -> bool:
    return _BLOCKQUOTE_RE.match(line) is not None


def _is_list_item(line: str) -> bool:
    return _LIST_ITEM_RE.match(line) is not None


def _is_list_continuation(line: str) -> bool:
    return line.startswith((" ", "\t"))


_ATOMIC_BLOCK_PATTERNS: tuple[tuple[Callable[[str], bool], Callable[[str], bool] | None], ...] = (
    (_is_table_row, None),
    (_is_blockquote, None),
    (_is_list_item, _is_list_continuation),
)


def _flush(buf: list[str], blocks: list[tuple[list[str], str]], headings: list[str]) -> None:
    if buf:
        blocks.append((list(headings), "".join(buf)))
        buf.clear()


def _consume_run(
    lines: list[str],
    start: int,
    predicate: Callable[[str], bool],
    continuation: Callable[[str], bool] | None,
) -> tuple[list[str], int]:
    out = [lines[start]]
    i = start + 1
    while i < len(lines) and (predicate(lines[i]) or (continuation and continuation(lines[i]))):
        out.append(lines[i])
        i += 1
    return out, i


def _consume_fence(lines: list[str], start: int, fence: str) -> tuple[list[str], int]:
    out = [lines[start]]
    i = start + 1
    while i < len(lines):
        out.append(lines[i])
        if lines[i].startswith(fence):
            i += 1
            break
        i += 1
    return out, i


class MarkdownChunker:
    """Splits Markdown by headings and atomic blocks (code, tables, lists, quotes).

    Heading-bounded chunks have no overlap; `chunk_overlap` applies only when a
    paragraph section exceeds `chunk_size` and is split via the inner
    `RecursiveCharacterChunker` fallback. Heading hierarchy is prepended to
    each chunk's content and exposed in `chunk.metadata['headings']`.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        heading_levels: tuple[int, ...] = (1, 2, 3),
    ) -> None:
        if chunk_size <= 0:
            raise ConfigurationError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ConfigurationError("chunk_overlap must be in [0, chunk_size)")
        if not heading_levels or any(lvl < 1 or lvl > 6 for lvl in heading_levels):
            raise ConfigurationError("heading_levels must be a non-empty subset of 1..6")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.heading_levels = set(heading_levels)
        self._fallback = RecursiveCharacterChunker(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def chunk(self, document: Document) -> list[Chunk]:
        if not document.content:
            return []
        blocks = self._segment(document.content)
        out: list[Chunk] = []
        position = 0
        for headings, body in blocks:
            prefix = self._prefix(headings)
            full = f"{prefix}{body}".rstrip() + "\n"
            if len(full) <= self.chunk_size or self._is_atomic(body):
                out.append(self._make_chunk(document, full, position, headings))
                position += 1
                continue
            inner_doc = Document(id=document.id, content=full, metadata=document.metadata)
            inner_chunks = self._fallback.chunk(inner_doc)
            for ic in inner_chunks:
                merged_meta = deepcopy(document.metadata)
                merged_meta["headings"] = list(headings)
                out.append(
                    Chunk(
                        id=Chunk.make_id(document.id, position),
                        document_id=document.id,
                        content=ic.content,
                        position=position,
                        metadata=merged_meta,
                        content_hash=hashlib.sha256(ic.content.encode()).hexdigest(),
                    )
                )
                position += 1
        logger.debug(
            "MarkdownChunker: document %s -> %d chunks (%d blocks)",
            document.id,
            len(out),
            len(blocks),
        )
        return out

    def _segment(self, text: str) -> list[tuple[list[str], str]]:
        blocks: list[tuple[list[str], str]] = []
        lines = text.splitlines(keepends=True)
        headings: list[str] = []
        buf: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            heading_match = _HEADING_RE.match(line)
            if heading_match and len(heading_match.group(1)) in self.heading_levels:
                _flush(buf, blocks, headings)
                level = len(heading_match.group(1))
                headings = [*headings[: level - 1], heading_match.group(2).strip()]
                i += 1
                continue
            fence_match = _FENCE_RE.match(line)
            if fence_match:
                block_lines, i = _consume_fence(lines, i, fence_match.group(1))
                _flush(buf, blocks, headings)
                blocks.append((list(headings), "".join(block_lines)))
                continue
            for predicate, continuation in _ATOMIC_BLOCK_PATTERNS:
                if predicate(line):
                    block_lines, i = _consume_run(lines, i, predicate, continuation)
                    _flush(buf, blocks, headings)
                    blocks.append((list(headings), "".join(block_lines)))
                    break
            else:
                buf.append(line)
                i += 1
        _flush(buf, blocks, headings)
        return [(h, b) for h, b in blocks if b.strip()]

    @staticmethod
    def _is_atomic(body: str) -> bool:
        """Detects atomic blocks (fences/tables/lists/quotes) that must not be split.

        Redundant for blocks emitted by `_segment` (already grouped), but acts as a
        safety net if callers ever hand-construct block bodies.
        """
        first = body.lstrip().splitlines()[0] if body.strip() else ""
        return bool(
            _FENCE_RE.match(first)
            or _is_table_row(first)
            or _is_list_item(first)
            or _is_blockquote(first)
        )

    @staticmethod
    def _prefix(headings: list[str]) -> str:
        if not headings:
            return ""
        return "".join(f"{'#' * (i + 1)} {h}\n" for i, h in enumerate(headings)) + "\n"

    @staticmethod
    def _make_chunk(document: Document, content: str, position: int, headings: list[str]) -> Chunk:
        meta = deepcopy(document.metadata)
        meta["headings"] = list(headings)
        return Chunk(
            id=Chunk.make_id(document.id, position),
            document_id=document.id,
            content=content,
            position=position,
            metadata=meta,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
        )
