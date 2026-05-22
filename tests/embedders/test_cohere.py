"""Tests for CohereEmbedder. respx-mocked HTTP."""

from __future__ import annotations

import hashlib

import httpx
import respx

from cenote.embedders import CohereEmbedder
from cenote.models import Chunk


def _chunk(text: str, idx: int = 0) -> Chunk:
    return Chunk(
        id=f"d:{idx}",
        document_id="d",
        content=text,
        position=idx,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )


COHERE_URL = "https://api.cohere.com/v2/embed"


class TestCohereEmbedder:
    async def test_model_id_and_dimensions(self) -> None:
        e = CohereEmbedder(api_key="x", model="embed-multilingual-v3.0", dimensions=1024)
        assert e.model_id == "cohere:embed-multilingual-v3.0"
        assert e.dimensions == 1024

    @respx.mock
    async def test_embed_batch_returns_embedded_chunks_in_order(self) -> None:
        respx.post(COHERE_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "abc",
                    "embeddings": {"float": [[0.1] * 4, [0.2] * 4]},
                    "texts": ["first", "second"],
                    "meta": {"api_version": {"version": "2"}},
                },
            )
        )
        e = CohereEmbedder(api_key="k", model="embed-multilingual-v3.0", dimensions=4)
        out = await e.embed([_chunk("first", 0), _chunk("second", 1)])
        assert [o.chunk.content for o in out] == ["first", "second"]
        assert out[0].embedding == [0.1] * 4

    @respx.mock
    async def test_authorization_header(self) -> None:
        respx.post(COHERE_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "x",
                    "embeddings": {"float": [[0.0] * 4]},
                    "texts": ["x"],
                    "meta": {"api_version": {"version": "2"}},
                },
            )
        )
        e = CohereEmbedder(api_key="secret", model="embed-multilingual-v3.0", dimensions=4)
        await e.embed([_chunk("x")])
        sent = respx.calls.last.request
        assert sent.headers["authorization"] == "Bearer secret"

    @respx.mock
    async def test_embed_query_uses_input_type_search_query(self) -> None:
        respx.post(COHERE_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "x",
                    "embeddings": {"float": [[0.5] * 4]},
                    "texts": ["q"],
                    "meta": {"api_version": {"version": "2"}},
                },
            )
        )
        e = CohereEmbedder(api_key="k", model="embed-multilingual-v3.0", dimensions=4)
        v = await e.embed_query("hello")
        assert v == [0.5] * 4
        body = respx.calls.last.request.read().decode()
        assert "search_query" in body

    @respx.mock
    async def test_retries_then_succeeds(self) -> None:
        respx.post(COHERE_URL).mock(
            side_effect=[
                httpx.Response(429, json={"message": "rate limited"}),
                httpx.Response(
                    200,
                    json={
                        "id": "x",
                        "embeddings": {"float": [[0.9] * 4]},
                        "texts": ["x"],
                        "meta": {"api_version": {"version": "2"}},
                    },
                ),
            ]
        )
        e = CohereEmbedder(
            api_key="k",
            model="embed-multilingual-v3.0",
            dimensions=4,
            max_retries=2,
            base_backoff_seconds=0,
        )
        out = await e.embed([_chunk("x")])
        assert out[0].embedding == [0.9] * 4
