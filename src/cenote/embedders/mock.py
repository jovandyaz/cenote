# SPDX-License-Identifier: Apache-2.0
"""MockEmbedder — deterministic unit-norm vectors derived from content."""

from __future__ import annotations

import hashlib
import logging
import math
import random

from cenote.errors import ConfigurationError
from cenote.models import Chunk, EmbeddedChunk

logger = logging.getLogger(__name__)


class MockEmbedder:
    """Deterministic unit-norm embedder for tests and demos (no network)."""

    def __init__(self, dimensions: int = 1024, model_name: str = "default") -> None:
        if dimensions <= 0:
            raise ConfigurationError("dimensions must be positive")
        self._dimensions = dimensions
        self._model_name = model_name

    @property
    def model_id(self) -> str:
        return f"mock:{self._model_name}"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        logger.debug("MockEmbedder embedding %d chunks", len(chunks))
        return [
            EmbeddedChunk(
                chunk=c,
                embedding=self._vector_from_text(c.content),
                embedding_model=self.model_id,
                dimensions=self._dimensions,
            )
            for c in chunks
        ]

    async def embed_query(self, query: str) -> list[float]:
        return self._vector_from_text(query)

    def _vector_from_text(self, text: str) -> list[float]:
        # Unit-norm to match Voyage/Cohere distribution; raw Gaussian vectors
        # exhibit concentration of measure and hide ranking bugs in tests.
        seed_bytes = hashlib.sha256(text.encode()).digest()
        seed_int = int.from_bytes(seed_bytes[:8], "big")
        rng = random.Random(seed_int)
        raw = [rng.gauss(0.0, 1.0) for _ in range(self._dimensions)]
        norm = math.sqrt(sum(x * x for x in raw)) or 1.0
        return [x / norm for x in raw]
