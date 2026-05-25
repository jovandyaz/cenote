"""Tests for VoyageEmbedder. Uses respx to mock HTTP — no real API calls."""

from __future__ import annotations

import asyncio
import hashlib
import json

import httpx
import pytest
import respx

from cenote.embedders import VoyageEmbedder
from cenote.errors import ConfigurationError
from cenote.models import Chunk


def _chunk(text: str, idx: int = 0) -> Chunk:
    return Chunk(
        id=f"d:{idx}",
        document_id="d",
        content=text,
        position=idx,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )


VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"


class TestVoyageEmbedder:
    async def test_model_id_and_dimensions(self) -> None:
        e = VoyageEmbedder(api_key="x", model="voyage-3", dimensions=1024)
        assert e.model_id == "voyage:voyage-3"
        assert e.dimensions == 1024

    @respx.mock
    async def test_embed_batch_returns_embedded_chunks_in_order(self) -> None:
        route = respx.post(VOYAGE_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [
                        {"index": 0, "embedding": [0.1] * 4},
                        {"index": 1, "embedding": [0.2] * 4},
                    ],
                    "model": "voyage-3",
                    "usage": {"total_tokens": 12},
                },
            )
        )
        e = VoyageEmbedder(api_key="k", model="voyage-3", dimensions=4)
        chunks = [_chunk("first", 0), _chunk("second", 1)]
        out = await e.embed(chunks)
        assert route.called
        assert [o.chunk.content for o in out] == ["first", "second"]
        assert out[0].embedding == [0.1] * 4
        assert out[1].embedding == [0.2] * 4
        assert all(o.embedding_model == "voyage:voyage-3" for o in out)
        assert all(o.dimensions == 4 for o in out)

    @respx.mock
    async def test_authorization_header(self) -> None:
        respx.post(VOYAGE_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [{"index": 0, "embedding": [0.0] * 4}],
                    "model": "voyage-3",
                    "usage": {"total_tokens": 1},
                },
            )
        )
        e = VoyageEmbedder(api_key="secret-key", model="voyage-3", dimensions=4)
        await e.embed([_chunk("x")])
        sent = respx.calls.last.request
        assert sent.headers["authorization"] == "Bearer secret-key"

    @respx.mock
    async def test_embed_query_uses_input_type_query(self) -> None:
        respx.post(VOYAGE_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [{"index": 0, "embedding": [0.5] * 4}],
                    "model": "voyage-3",
                    "usage": {"total_tokens": 1},
                },
            )
        )
        e = VoyageEmbedder(api_key="k", model="voyage-3", dimensions=4)
        v = await e.embed_query("search query")
        assert v == [0.5] * 4
        body = respx.calls.last.request.read().decode()
        assert "input_type" in body and "query" in body

    @respx.mock
    async def test_retries_on_5xx_then_succeeds(self) -> None:
        respx.post(VOYAGE_URL).mock(
            side_effect=[
                httpx.Response(503, json={"error": "transient"}),
                httpx.Response(
                    200,
                    json={
                        "data": [{"index": 0, "embedding": [0.7] * 4}],
                        "model": "voyage-3",
                        "usage": {"total_tokens": 1},
                    },
                ),
            ]
        )
        e = VoyageEmbedder(
            api_key="k", model="voyage-3", dimensions=4, max_retries=2, base_backoff_seconds=0
        )
        out = await e.embed([_chunk("x")])
        assert out[0].embedding == [0.7] * 4

    @respx.mock
    async def test_gives_up_after_max_retries(self) -> None:
        respx.post(VOYAGE_URL).mock(return_value=httpx.Response(500, json={"error": "boom"}))
        e = VoyageEmbedder(
            api_key="k", model="voyage-3", dimensions=4, max_retries=2, base_backoff_seconds=0
        )
        with pytest.raises(httpx.HTTPStatusError):
            await e.embed([_chunk("x")])

    @respx.mock
    async def test_batches_large_input_into_multiple_requests(self) -> None:
        """250 chunks with batch_size=128 → 2 HTTP calls."""

        def _resp(req: httpx.Request) -> httpx.Response:
            body = json.loads(req.read().decode())
            n = len(body["input"])
            return httpx.Response(
                200,
                json={
                    "data": [{"index": i, "embedding": [0.1 * i] * 4} for i in range(n)],
                    "model": "voyage-3",
                    "usage": {"total_tokens": n},
                },
            )

        route = respx.post(VOYAGE_URL).mock(side_effect=_resp)
        e = VoyageEmbedder(
            api_key="k",
            model="voyage-3",
            dimensions=4,
            batch_size=128,
            max_concurrency=4,
        )
        chunks = [_chunk(f"chunk-{i}", i) for i in range(250)]
        out = await e.embed(chunks)
        assert len(out) == 250
        assert route.call_count == 2  # 128 + 122
        assert [o.chunk.content for o in out] == [c.content for c in chunks]

    @respx.mock
    async def test_max_concurrency_caps_in_flight_requests(self) -> None:
        """5 batches with max_concurrency=2 → never more than 2 simultaneous calls."""
        in_flight = 0
        peak = 0
        lock = asyncio.Lock()

        async def _resp(req: httpx.Request) -> httpx.Response:
            nonlocal in_flight, peak
            async with lock:
                in_flight += 1
                peak = max(peak, in_flight)
            await asyncio.sleep(0.05)
            async with lock:
                in_flight -= 1
            body = json.loads(req.read().decode())
            n = len(body["input"])
            return httpx.Response(
                200,
                json={
                    "data": [{"index": i, "embedding": [0.0] * 4} for i in range(n)],
                    "model": "voyage-3",
                    "usage": {"total_tokens": n},
                },
            )

        respx.post(VOYAGE_URL).mock(side_effect=_resp)
        e = VoyageEmbedder(
            api_key="k",
            model="voyage-3",
            dimensions=4,
            batch_size=10,
            max_concurrency=2,
        )
        chunks = [_chunk(f"c-{i}", i) for i in range(50)]  # 5 batches
        await e.embed(chunks)
        assert peak <= 2, f"max concurrency exceeded: peak={peak}"

    def test_batch_size_validation(self) -> None:
        with pytest.raises(ConfigurationError):
            VoyageEmbedder(api_key="k", batch_size=0)
        with pytest.raises(ConfigurationError):
            VoyageEmbedder(api_key="k", batch_size=200)  # > VOYAGE_MAX_BATCH
