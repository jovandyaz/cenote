# SPDX-License-Identifier: Apache-2.0
"""cenote — production-grade agentic RAG primitives."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("pycenote")
except PackageNotFoundError:  # uninstalled (dev) checkout
    __version__ = "0.0.0+dev"

from cenote.errors import (
    CenoteError,
    ConfigurationError,
    DimensionMismatchError,
    EmbeddingError,
    MigrationError,
    RateLimitError,
    VectorStoreError,
)
from cenote.types import ContentHash, ModelId, Namespace, Vector

__all__ = [
    "CenoteError",
    "ConfigurationError",
    "ContentHash",
    "DimensionMismatchError",
    "EmbeddingError",
    "MigrationError",
    "ModelId",
    "Namespace",
    "RateLimitError",
    "Vector",
    "VectorStoreError",
    "__version__",
]
