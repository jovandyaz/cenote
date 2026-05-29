# SPDX-License-Identifier: Apache-2.0
"""BenchRunner — orchestrates BM25 / vector / hybrid retrieval over MIRACL data."""

from __future__ import annotations

import logging
from typing import Literal

from cenote.bench.metrics import RunDict, rrf_fuse
from cenote.bench.miracl import MiraclLoader
from cenote.embedders.base import Embedder
from cenote.retrievers import BM25Retriever, VectorRetriever
from cenote.stores.base import VectorStore
from cenote.tokenizers.base import Tokenizer

logger = logging.getLogger(__name__)

RetrieverName = Literal["bm25", "vector", "hybrid"]
_KNOWN: frozenset[str] = frozenset({"bm25", "vector", "hybrid"})


class BenchRunner:
    """Index the loader's corpus, then run any combination of BM25/vector/hybrid."""

    def __init__(
        self,
        *,
        loader: MiraclLoader,
        embedder: Embedder,
        store: VectorStore,
        tokenizer: Tokenizer,
    ) -> None:
        self._loader = loader
        self._embedder = embedder
        self._store = store
        self._tokenizer = tokenizer
        self._bm25: BM25Retriever | None = None
        self._vector: VectorRetriever | None = None
        self._indexed = False

    async def index(self) -> int:
        """Embed the corpus and upsert it to the store. Returns the chunk count."""
        chunks = [c async for c in self._loader.load_corpus()]
        embedded = await self._embedder.embed(chunks)
        await self._store.upsert(embedded, namespace=self._loader.namespace)
        self._bm25 = BM25Retriever(store=self._store, tokenizer=self._tokenizer)
        self._vector = VectorRetriever(embedder=self._embedder, store=self._store)
        self._indexed = True
        logger.info(
            "BenchRunner indexed %d chunks for namespace %s", len(chunks), self._loader.namespace
        )
        return len(chunks)

    async def run_all(
        self,
        retrievers: list[str],
        top_k: int = 1000,
        rrf_k: int = 60,
    ) -> dict[str, RunDict]:
        """Execute each requested retriever; hybrid auto-runs its bm25+vector components."""
        if not self._indexed:
            raise RuntimeError("call index() before run_all()")
        unknown = set(retrievers) - _KNOWN
        if unknown:
            raise ValueError(f"unknown retriever names: {sorted(unknown)}")

        queries = await self._loader.load_queries()
        runs: dict[str, RunDict] = {}
        needs_bm25 = "bm25" in retrievers or "hybrid" in retrievers
        needs_vector = "vector" in retrievers or "hybrid" in retrievers
        if needs_bm25:
            runs["bm25"] = await self._execute(self._bm25, queries, top_k)
        if needs_vector:
            runs["vector"] = await self._execute(self._vector, queries, top_k)
        if "hybrid" in retrievers:
            runs["hybrid"] = rrf_fuse([runs["bm25"], runs["vector"]], k=rrf_k)
        return {name: runs[name] for name in retrievers}

    async def _execute(
        self,
        retriever: BM25Retriever | VectorRetriever | None,
        queries: dict[str, str],
        top_k: int,
    ) -> RunDict:
        assert retriever is not None
        run: RunDict = {}
        for qid, query_text in queries.items():
            results = await retriever.retrieve(
                query_text, namespace=self._loader.namespace, limit=top_k
            )
            run[qid] = {r.chunk.id: r.score for r in results}
        return run
