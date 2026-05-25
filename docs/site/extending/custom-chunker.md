# Custom chunker

The `Chunker` protocol is minimal — implement `chunk(document) -> list[Chunk]` and you're done.

## The protocol

::: cenote.chunkers.base.Chunker

## Contract

The Protocol docstring lays out the load-bearing invariant: `chunk.content` is the exact text that will be embedded. Implementations that prepend contextual information (heading hierarchy, code-block fences) must include that context in `chunk.content` itself, not only in `chunk.metadata`. The embedding cache keys off `(model_id, sha256(chunk.content))`; two chunks with the same body but different prepended context would otherwise collide.

## Minimal example

```python
from cenote.models import Chunk, Document
import hashlib


class SentenceChunker:
    """Splits on sentence boundaries (naive — period + space)."""

    def chunk(self, document: Document) -> list[Chunk]:
        sentences = [s.strip() for s in document.content.split(". ") if s.strip()]
        return [
            Chunk(
                id=Chunk.make_id(document.id, i),
                document_id=document.id,
                content=sentence,
                position=i,
                metadata=dict(document.metadata),
                content_hash=hashlib.sha256(sentence.encode()).hexdigest(),
            )
            for i, sentence in enumerate(sentences)
        ]
```

For production-quality sentence splitting, consider wrapping `spaCy` or `nltk` — but mind the new runtime dependency.
