# SPDX-License-Identifier: Apache-2.0
"""Exception hierarchy for cenote. All raised errors inherit from CenoteError."""

from __future__ import annotations


class CenoteError(Exception):
    """Base class for all cenote-raised exceptions."""


class ConfigurationError(CenoteError):
    """Invalid construction parameters (bad dimensions, missing api_key, etc.)."""


class EmbeddingError(CenoteError):
    """Failure during embedding generation."""


class RateLimitError(EmbeddingError):
    """Provider rate limit hit after exhausting retries."""


class VectorStoreError(CenoteError):
    """Failure interacting with a vector store."""


class DimensionMismatchError(VectorStoreError):
    """Embedding dimensions do not match store dimensions."""


class MigrationError(VectorStoreError):
    """Schema migration failure."""
