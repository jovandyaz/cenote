# SPDX-License-Identifier: Apache-2.0
"""CohereReranker — cross-encoder reranking via Cohere v2 rerank API."""

from __future__ import annotations

from typing import Any, ClassVar

from cenote.rerankers._http_reranker import _HTTPReranker

COHERE_RERANK_URL = "https://api.cohere.com/v2/rerank"
COHERE_RERANK_MAX_BATCH = 1000


class CohereReranker(_HTTPReranker):
    """Cohere multilingual reranker (default model `rerank-3.5-multilingual`)."""

    _PROVIDER: ClassVar[str] = "cohere"
    _URL: ClassVar[str] = COHERE_RERANK_URL
    _MAX_BATCH: ClassVar[int] = COHERE_RERANK_MAX_BATCH
    _DEFAULT_MODEL: ClassVar[str] = "rerank-3.5-multilingual"
    _RESPONSE_KEY: ClassVar[str] = "results"
    _EXTRA_HEADERS: ClassVar[dict[str, str]] = {"accept": "application/json"}

    def _payload(self, query: str, documents: list[str]) -> dict[str, Any]:
        return {"model": self._model, "query": query, "documents": documents}
