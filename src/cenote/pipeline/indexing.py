# SPDX-License-Identifier: Apache-2.0
"""IndexingPipeline — orchestrates Chunker -> Embedder -> VectorStore with progress.

Continues past per-batch failures (logged + counted in `errors`). Yields
IndexingProgress after each batch so callers can stream UI updates.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass

from cenote.chunkers.base import Chunker
from cenote.embedders.base import Embedder
from cenote.errors import ConfigurationError
from cenote.models import Chunk, Document
from cenote.stores.base import VectorStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IndexingProgress:
    """Snapshot emitted by IndexingPipeline.index() per batch."""

    documents_done: int
    chunks_done: int
    errors: int


class IndexingPipeline:
    """Indexes documents end-to-end: chunk -> embed (batched) -> upsert.

    Continues past per-batch failures (logged + counted in `errors`).
    Yields IndexingProgress after each batch so callers can stream UI updates.

    Failure model: an embedder or store exception on a single batch does NOT
    abort the run. The failing batch's chunks are dropped (not retried inside
    the pipeline), the error counter increments, and the next batch proceeds.
    Callers that need stricter "all or nothing" semantics should check
    `final.errors == 0` and retry the document set themselves.
    """

    def __init__(
        self,
        chunker: Chunker,
        embedder: Embedder,
        store: VectorStore,
        *,
        namespace: str,
        batch_size: int = 32,
    ) -> None:
        if batch_size <= 0:
            raise ConfigurationError("batch_size must be positive")
        self._chunker = chunker
        self._embedder = embedder
        self._store = store
        self._namespace = namespace
        self._batch_size = batch_size

    async def index(self, documents: Iterable[Document]) -> AsyncIterator[IndexingProgress]:
        """Index documents, yielding progress after each batch.

        Empty document iterables yield no progress events. Documents that
        produce zero chunks (e.g., empty content) still count toward
        `documents_done` but contribute no chunks.
        """
        docs_done = 0
        chunks_done = 0
        errors = 0
        pending: list[Chunk] = []

        for doc in documents:
            chunks = self._chunker.chunk(doc)
            docs_done += 1
            pending.extend(chunks)
            while len(pending) >= self._batch_size:
                batch = pending[: self._batch_size]
                pending = pending[self._batch_size :]
                try:
                    embedded = await self._embedder.embed(batch)
                    await self._store.upsert(embedded, namespace=self._namespace)
                    chunks_done += len(batch)
                except Exception as exc:
                    logger.warning("IndexingPipeline batch failed: %s", exc)
                    errors += 1
                yield IndexingProgress(docs_done, chunks_done, errors)

        if pending:
            try:
                embedded = await self._embedder.embed(pending)
                await self._store.upsert(embedded, namespace=self._namespace)
                chunks_done += len(pending)
            except Exception as exc:
                logger.warning("IndexingPipeline final batch failed: %s", exc)
                errors += 1
            yield IndexingProgress(docs_done, chunks_done, errors)
