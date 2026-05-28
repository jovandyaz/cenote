# SPDX-License-Identifier: Apache-2.0
"""Performance benchmark for BM25Retriever index construction over realistic corpora."""

from __future__ import annotations

import pytest

from cenote.models import Chunk
from cenote.retrievers.bm25 import BM25Retriever
from cenote.tokenizers.spanish import SpanishTokenizer


@pytest.mark.benchmark
def test_bm25_build_index_1000_chunks(benchmark) -> None:
    """Build a BM25 index over 1000 Spanish chunks via SpanishTokenizer."""
    tokenizer = SpanishTokenizer()
    chunks = [
        Chunk(
            id=f"c{i}",
            document_id=f"d{i // 10}",
            content=(
                f"documento numero {i} con contenido variado y palabras "
                "suficientes para tokenizar correctamente"
            ),
            position=i,
            content_hash=f"hash{i}",
        )
        for i in range(1000)
    ]

    def _build() -> None:
        BM25Retriever.from_chunks(chunks, tokenizer=tokenizer)

    benchmark(_build)
