# SPDX-License-Identifier: Apache-2.0
"""BM25Retriever — Okapi BM25 over chunks pulled from any VectorStore."""

from __future__ import annotations

import logging
from typing import Any

from rank_bm25 import BM25Okapi

from cenote._filters import matches_filter
from cenote.models import Chunk, RetrievalResult
from cenote.stores.base import VectorStore
from cenote.tokenizers.base import Tokenizer

logger = logging.getLogger(__name__)


class BM25Retriever:
    """BM25-Okapi retriever over chunks loaded lazily from a VectorStore.

    The per-namespace index is built on first `retrieve()` and cached for the
    retriever instance lifetime. Use `from_chunks` for ad-hoc indexing without
    a store (useful in tests and one-shot benchmarks).
    """

    def __init__(
        self,
        store: VectorStore | None,
        tokenizer: Tokenizer,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self._store = store
        self._tokenizer = tokenizer
        self._k1 = k1
        self._b = b
        # Concurrent cold-cache calls may double-build; benign because BM25Okapi
        # is deterministic on the same input — last writer wins, no corruption.
        self._caches: dict[str, tuple[BM25Okapi, list[Chunk]]] = {}

    @classmethod
    def from_chunks(
        cls,
        chunks: list[Chunk],
        tokenizer: Tokenizer,
        k1: float = 1.5,
        b: float = 0.75,
        namespace: str = "default",
    ) -> BM25Retriever:
        """Construct directly from pre-loaded chunks; no VectorStore needed."""
        retriever = cls(store=None, tokenizer=tokenizer, k1=k1, b=b)
        retriever._caches[namespace] = retriever._build_index(chunks)
        return retriever

    async def retrieve(
        self,
        query: str,
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        if namespace not in self._caches:
            if self._store is None:
                logger.debug("BM25Retriever: no store and namespace %s missing", namespace)
                return []
            chunks = [c async for c in self._store.get_all_chunks(namespace=namespace)]
            if not chunks:
                return []
            self._caches[namespace] = self._build_index(chunks)
        bm25, chunks = self._caches[namespace]
        tokens = self._tokenizer.tokenize(query)
        full_scores = bm25.get_scores(tokens)
        if filter:
            scored: list[tuple[float, Chunk]] = [
                (float(full_scores[i]), c)
                for i, c in enumerate(chunks)
                if matches_filter(c.metadata, filter)
            ]
        else:
            scored = [(float(s), c) for s, c in zip(full_scores, chunks, strict=True)]
        scored.sort(key=lambda t: t[0], reverse=True)
        return [RetrievalResult(chunk=c, score=s, retriever="bm25") for s, c in scored[:limit]]

    def _build_index(self, chunks: list[Chunk]) -> tuple[BM25Okapi, list[Chunk]]:
        tokenized = [self._tokenizer.tokenize(c.content) for c in chunks]
        bm25 = BM25Okapi(tokenized, k1=self._k1, b=self._b)
        logger.debug("BM25Retriever built index with %d documents", len(chunks))
        return bm25, list(chunks)
