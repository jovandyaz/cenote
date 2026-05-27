# SPDX-License-Identifier: Apache-2.0
"""Shared HTTP rerank machinery — base class for provider-specific impls."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

import httpx

from cenote.embedders._http import RateLimiter, retrying
from cenote.errors import ConfigurationError
from cenote.models import RetrievalResult

logger = logging.getLogger(__name__)


class _HTTPReranker:
    """Shared HTTP rerank machinery; subclasses set provider constants + payload shape."""

    _PROVIDER: ClassVar[str] = ""
    _URL: ClassVar[str] = ""
    _MAX_BATCH: ClassVar[int] = 1000
    _DEFAULT_MODEL: ClassVar[str] = ""
    _RESPONSE_KEY: ClassVar[str] = "data"
    _EXTRA_HEADERS: ClassVar[dict[str, str]] = {}

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        base_backoff_seconds: float = 0.5,
        batch_size: int | None = None,
        max_concurrency: int = 4,
        requests_per_minute: int | None = None,
    ) -> None:
        if not api_key:
            raise ConfigurationError("api_key is required")
        batch = batch_size if batch_size is not None else self._MAX_BATCH
        if not 0 < batch <= self._MAX_BATCH:
            raise ConfigurationError(f"batch_size must be in (0, {self._MAX_BATCH}]")
        if max_concurrency <= 0:
            raise ConfigurationError("max_concurrency must be positive")
        self._api_key = api_key
        self._model = model or self._DEFAULT_MODEL
        self._base_url = base_url or self._URL
        self._timeout = timeout
        self._max_retries = max_retries
        self._base_backoff_seconds = base_backoff_seconds
        self._batch_size = batch
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._rate_limiter = RateLimiter(requests_per_minute) if requests_per_minute else None

    @property
    def model_id(self) -> str:
        return f"{self._PROVIDER}:{self._model}"

    def _payload(self, query: str, documents: list[str]) -> dict[str, Any]:
        return {"query": query, "documents": documents, "model": self._model}

    async def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        if not results:
            return []
        batches = [
            results[i : i + self._batch_size] for i in range(0, len(results), self._batch_size)
        ]
        logger.debug(
            "%s dispatching %d batches (batch_size=%d) for %d results",
            type(self).__name__,
            len(batches),
            self._batch_size,
            len(results),
        )
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            scored_batches = await asyncio.gather(
                *[self._rerank_batch(client, query, b) for b in batches]
            )
        merged: list[RetrievalResult] = [r for batch in scored_batches for r in batch]
        merged.sort(key=lambda r: r.score, reverse=True)
        return merged[:top_k] if top_k is not None else merged

    async def _rerank_batch(
        self,
        client: httpx.AsyncClient,
        query: str,
        batch: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        async with self._semaphore:
            scored = await self._call_api(client, query, [r.chunk.content for r in batch])
        seen: set[int] = set()
        out: list[RetrievalResult] = []
        for item in scored:
            idx = int(item["index"])
            if idx in seen or not 0 <= idx < len(batch):
                logger.warning(
                    "%s returned invalid index %d (batch_size=%d)",
                    type(self).__name__,
                    idx,
                    len(batch),
                )
                continue
            seen.add(idx)
            base = batch[idx]
            out.append(
                RetrievalResult(
                    chunk=base.chunk,
                    score=float(item["relevance_score"]),
                    retriever=f"{base.retriever}+rerank:{self._PROVIDER}",
                )
            )
        return out

    async def _call_api(
        self, client: httpx.AsyncClient, query: str, documents: list[str]
    ) -> list[dict[str, Any]]:
        payload = self._payload(query, documents)
        headers = {
            "authorization": f"Bearer {self._api_key}",
            "content-type": "application/json",
            **self._EXTRA_HEADERS,
        }

        async def _attempt() -> httpx.Response:
            if self._rate_limiter is not None:
                async with self._rate_limiter:
                    return await client.post(self._base_url, headers=headers, json=payload)
            return await client.post(self._base_url, headers=headers, json=payload)

        response = await retrying(
            _attempt,
            max_retries=self._max_retries,
            base_backoff_seconds=self._base_backoff_seconds,
        )
        return list(response.json()[self._RESPONSE_KEY])
