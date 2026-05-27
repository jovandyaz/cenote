# SPDX-License-Identifier: Apache-2.0
"""Tests for CohereReranker — respx-mocked HTTP, no real API calls."""

from __future__ import annotations

import httpx
import pytest
import respx

from cenote.errors import ConfigurationError, RateLimitError
from cenote.rerankers import CohereReranker
from cenote.rerankers.cohere import COHERE_RERANK_URL
from tests._factories import make_result


@pytest.mark.asyncio
class TestCohereReranker:
    async def test_rejects_missing_api_key(self) -> None:
        with pytest.raises(ConfigurationError):
            CohereReranker(api_key="")

    async def test_model_id_format(self) -> None:
        r = CohereReranker(api_key="k", model="rerank-3.5-multilingual")
        assert r.model_id == "cohere:rerank-3.5-multilingual"

    @respx.mock
    async def test_reorders_by_relevance(self) -> None:
        respx.post(COHERE_RERANK_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {"index": 1, "relevance_score": 0.95},
                        {"index": 0, "relevance_score": 0.20},
                    ]
                },
            )
        )
        reranker = CohereReranker(api_key="k")
        inputs = [make_result("first", 0.9, idx=0), make_result("second", 0.1, idx=1)]
        out = await reranker.rerank("query", inputs)
        assert [r.chunk.content for r in out] == ["second", "first"]
        assert out[0].score == pytest.approx(0.95)
        assert out[0].retriever == "vector+rerank:cohere"

    @respx.mock
    async def test_top_k_caps_output(self) -> None:
        respx.post(COHERE_RERANK_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [{"index": i, "relevance_score": (10 - i) / 10} for i in range(10)]
                },
            )
        )
        reranker = CohereReranker(api_key="k")
        inputs = [make_result(f"t{i}", 0.0, idx=i) for i in range(10)]
        out = await reranker.rerank("q", inputs, top_k=3)
        assert len(out) == 3

    @respx.mock
    async def test_top_k_none_returns_all(self) -> None:
        respx.post(COHERE_RERANK_URL).mock(
            return_value=httpx.Response(
                200,
                json={"results": [{"index": i, "relevance_score": (5 - i) / 5} for i in range(5)]},
            )
        )
        reranker = CohereReranker(api_key="k")
        inputs = [make_result(f"t{i}", 0.0, idx=i) for i in range(5)]
        out = await reranker.rerank("q", inputs)
        assert len(out) == 5

    @respx.mock
    async def test_retries_on_5xx(self) -> None:
        route = respx.post(COHERE_RERANK_URL).mock(
            side_effect=[
                httpx.Response(502),
                httpx.Response(
                    200,
                    json={"results": [{"index": 0, "relevance_score": 0.5}]},
                ),
            ]
        )
        reranker = CohereReranker(api_key="k", max_retries=2, base_backoff_seconds=0.0)
        out = await reranker.rerank("q", [make_result("x", 0.0)])
        assert route.call_count == 2
        assert out[0].score == pytest.approx(0.5)

    @respx.mock
    async def test_raises_rate_limit_after_retries(self) -> None:
        respx.post(COHERE_RERANK_URL).mock(return_value=httpx.Response(429))
        reranker = CohereReranker(api_key="k", max_retries=1, base_backoff_seconds=0.0)
        with pytest.raises(RateLimitError):
            await reranker.rerank("q", [make_result("x", 0.0)])

    @respx.mock
    async def test_authorization_header(self) -> None:
        route = respx.post(COHERE_RERANK_URL).mock(
            return_value=httpx.Response(
                200,
                json={"results": [{"index": 0, "relevance_score": 0.5}]},
            )
        )
        reranker = CohereReranker(api_key="secret-token")
        await reranker.rerank("q", [make_result("x", 0.0)])
        assert route.calls.last.request.headers["authorization"] == "Bearer secret-token"

    @respx.mock
    async def test_empty_results_short_circuits(self) -> None:
        route = respx.post(COHERE_RERANK_URL)
        reranker = CohereReranker(api_key="k")
        assert await reranker.rerank("q", []) == []
        assert route.call_count == 0

    @respx.mock
    async def test_invalid_index_in_response_is_skipped(self) -> None:
        respx.post(COHERE_RERANK_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {"index": 0, "relevance_score": 0.9},
                        {"index": 0, "relevance_score": 0.4},
                        {"index": 99, "relevance_score": 0.5},
                    ]
                },
            )
        )
        reranker = CohereReranker(api_key="k")
        out = await reranker.rerank("q", [make_result("only", 0.0)])
        assert len(out) == 1
        assert out[0].score == pytest.approx(0.9)
