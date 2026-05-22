# SPDX-License-Identifier: Apache-2.0
"""Retriever Protocol."""

from __future__ import annotations

from typing import Any, Protocol

from cenote.models import RetrievalResult


class Retriever(Protocol):
    """Returns ranked RetrievalResults for a query. `namespace` is mandatory."""

    async def retrieve(
        self,
        query: str,
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]: ...
