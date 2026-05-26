# Custom embedder

Implement the `Embedder` protocol from scratch — no inheritance required. Any class with the right shape satisfies the contract.

## The protocol

::: cenote.embedders.base.Embedder

## Minimal example

The full source is in [examples/custom_embedder.py](https://github.com/jovandyaz/cenote/blob/main/examples/custom_embedder.py).

```python
import hashlib
import math
import random
from cenote.models import Chunk, EmbeddedChunk


class HashEmbedder:
    """An embedder that derives deterministic unit-norm vectors from text hashes."""

    def __init__(self, dimensions: int = 256) -> None:
        self._dimensions = dimensions

    @property
    def model_id(self) -> str:
        return f"hash:{self._dimensions}"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        return [
            EmbeddedChunk(
                chunk=c,
                embedding=self._vec(c.content),
                embedding_model=self.model_id,
                dimensions=self._dimensions,
            )
            for c in chunks
        ]

    async def embed_query(self, query: str) -> list[float]:
        return self._vec(query)

    def _vec(self, text: str) -> list[float]:
        seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")
        rng = random.Random(seed)
        raw = [rng.gauss(0, 1) for _ in range(self._dimensions)]
        norm = math.sqrt(sum(x * x for x in raw)) or 1.0
        return [x / norm for x in raw]
```

This class satisfies the `Embedder` protocol by structural typing: it has the right methods and property shapes. Pass it directly to `VectorRetriever(embedder=HashEmbedder(), store=...)` — no `isinstance` check, no inheritance.

## Why unit-norm?

Real embedders (Voyage, Cohere) produce vectors close to the unit hypersphere. Cosine similarity between random Gaussian vectors in high dimensions concentrates near zero (concentration of measure), which makes rankings look random in tests. Normalizing your custom embedder to unit length matches production distribution.
