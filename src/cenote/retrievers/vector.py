# SPDX-License-Identifier: Apache-2.0
"""VectorRetriever — composes an Embedder with a VectorStore."""

from __future__ import annotations

import logging
from typing import Any

from cenote.embedders.base import Embedder
from cenote.models import RetrievalResult
from cenote.stores.base import VectorStore

logger = logging.getLogger(__name__)


class VectorRetriever:
    """Embed the query, then search the store."""

    def __init__(self, embedder: Embedder, store: VectorStore) -> None:
        self._embedder = embedder
        self._store = store

    async def retrieve(
        self,
        query: str,
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        logger.debug(
            "VectorRetriever: query='%s' namespace=%s limit=%d", query[:60], namespace, limit
        )
        vector = await self._embedder.embed_query(query)
        results = await self._store.search(vector, namespace=namespace, limit=limit, filter=filter)
        logger.debug("VectorRetriever: returned %d results", len(results))
        return [RetrievalResult(chunk=r.chunk, score=r.score, retriever="vector") for r in results]
