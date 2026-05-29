# SPDX-License-Identifier: Apache-2.0
"""BM25Retriever — Okapi BM25 over chunks pulled from any VectorStore."""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any

from rank_bm25 import BM25Okapi

from cenote._filters import matches_filter
from cenote.errors import ConfigurationError
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
        max_cached_namespaces: int = 128,
    ) -> None:
        if max_cached_namespaces <= 0:
            raise ConfigurationError("max_cached_namespaces must be positive")
        self._store = store
        self._tokenizer = tokenizer
        self._k1 = k1
        self._b = b
        self._max_cached = max_cached_namespaces
        # OrderedDict for LRU: move_to_end on access, popitem(last=False) on eviction.
        # Concurrent cold-cache calls may double-build; benign (BM25Okapi is deterministic).
        self._caches: OrderedDict[str, tuple[BM25Okapi, list[Chunk]]] = OrderedDict()

    @classmethod
    def from_chunks(
        cls,
        chunks: list[Chunk],
        tokenizer: Tokenizer,
        k1: float = 1.5,
        b: float = 0.75,
        namespace: str = "default",
        max_cached_namespaces: int = 128,
    ) -> BM25Retriever:
        """Construct directly from pre-loaded chunks; no VectorStore needed."""
        retriever = cls(
            store=None,
            tokenizer=tokenizer,
            k1=k1,
            b=b,
            max_cached_namespaces=max_cached_namespaces,
        )
        retriever._caches[namespace] = retriever._build_index(chunks)
        return retriever

    def invalidate(self, namespace: str) -> None:
        """Drop the cached BM25 index for `namespace`. No-op if absent.

        Callers should invoke this after upserting chunks into a namespace
        whose index is already cached, otherwise stale results may be returned
        for the retriever's lifetime.
        """
        self._caches.pop(namespace, None)

    async def retrieve(
        self,
        query: str,
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        if namespace in self._caches:
            self._caches.move_to_end(namespace)
        else:
            if self._store is None:
                logger.debug("BM25Retriever: no store and namespace %s missing", namespace)
                return []
            chunks = [c async for c in self._store.get_all_chunks(namespace=namespace)]
            if not chunks:
                return []
            self._caches[namespace] = self._build_index(chunks)
            while len(self._caches) > self._max_cached:
                evicted, _ = self._caches.popitem(last=False)
                logger.debug("BM25Retriever: evicted namespace %s from LRU cache", evicted)
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
