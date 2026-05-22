# SPDX-License-Identifier: Apache-2.0
"""VoyageEmbedder — embeds via the Voyage AI REST API with batching."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from cenote.embedders._http import RateLimiter, retrying
from cenote.models import Chunk, EmbeddedChunk

VOYAGE_BASE_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_MAX_BATCH = 128  # voyage-3 family API limit


class VoyageEmbedder:
    """Voyage AI embedder with batching, concurrency, and optional rate limiting.

    Splits inputs into `batch_size`-sized requests issued concurrently up to
    `max_concurrency`. Pass `requests_per_minute` for free-tier accounts (300 RPM).
    """

    def __init__(
        self,
        api_key: str,
        model: str = "voyage-3",
        dimensions: int = 1024,
        *,
        base_url: str = VOYAGE_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
        base_backoff_seconds: float = 0.5,
        batch_size: int = VOYAGE_MAX_BATCH,
        max_concurrency: int = 4,
        requests_per_minute: int | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        if not 0 < batch_size <= VOYAGE_MAX_BATCH:
            raise ValueError(f"batch_size must be in (0, {VOYAGE_MAX_BATCH}]")
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be positive")
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._base_url = base_url
        self._timeout = timeout
        self._max_retries = max_retries
        self._base_backoff_seconds = base_backoff_seconds
        self._batch_size = batch_size
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._rate_limiter = RateLimiter(requests_per_minute) if requests_per_minute else None

    @property
    def model_id(self) -> str:
        return f"voyage:{self._model}"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        if not chunks:
            return []
        batches = [
            chunks[i : i + self._batch_size] for i in range(0, len(chunks), self._batch_size)
        ]
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            results = await asyncio.gather(*[self._embed_batch(client, batch) for batch in batches])
        return [ec for batch_result in results for ec in batch_result]

    async def embed_query(self, query: str) -> list[float]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            vectors = await self._call_api(client, [query], input_type="query")
        return vectors[0]

    async def _embed_batch(
        self, client: httpx.AsyncClient, batch: list[Chunk]
    ) -> list[EmbeddedChunk]:
        async with self._semaphore:
            vectors = await self._call_api(
                client, [c.content for c in batch], input_type="document"
            )
        return [
            EmbeddedChunk(
                chunk=chunk,
                embedding=vector,
                embedding_model=self.model_id,
                dimensions=self._dimensions,
            )
            for chunk, vector in zip(batch, vectors, strict=True)
        ]

    async def _call_api(
        self,
        client: httpx.AsyncClient,
        inputs: list[str],
        *,
        input_type: str,
    ) -> list[list[float]]:
        payload: dict[str, Any] = {
            "input": inputs,
            "model": self._model,
            "input_type": input_type,
        }
        headers = {
            "authorization": f"Bearer {self._api_key}",
            "content-type": "application/json",
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
        data = response.json()
        items = sorted(data["data"], key=lambda d: d["index"])
        return [item["embedding"] for item in items]
