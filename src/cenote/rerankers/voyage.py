# SPDX-License-Identifier: Apache-2.0
"""VoyageReranker — cross-encoder reranking via Voyage AI."""

from __future__ import annotations

from typing import ClassVar

from cenote.rerankers._http_reranker import _HTTPReranker

VOYAGE_RERANK_URL = "https://api.voyageai.com/v1/rerank"
VOYAGE_RERANK_MAX_BATCH = 1000


class VoyageReranker(_HTTPReranker):
    """Voyage AI reranker (default model `rerank-2`)."""

    _PROVIDER: ClassVar[str] = "voyage"
    _URL: ClassVar[str] = VOYAGE_RERANK_URL
    _MAX_BATCH: ClassVar[int] = VOYAGE_RERANK_MAX_BATCH
    _DEFAULT_MODEL: ClassVar[str] = "rerank-2"
