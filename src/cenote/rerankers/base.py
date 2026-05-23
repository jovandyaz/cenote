# SPDX-License-Identifier: Apache-2.0
"""Reranker Protocol — public API surface only. Concrete impls land in M1.1."""

from __future__ import annotations

from typing import Protocol

from cenote.models import RetrievalResult


class Reranker(Protocol):
    """Re-orders RetrievalResults by relevance; score overwritten by reranker score,
    retriever set to '<original>+rerank:<provider>'. top_k caps the output list.
    """

    @property
    def model_id(self) -> str:
        """'provider:model_name', e.g. 'voyage:rerank-2', 'cohere:rerank-3.5'."""
        ...

    async def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int | None = None,
    ) -> list[RetrievalResult]: ...
