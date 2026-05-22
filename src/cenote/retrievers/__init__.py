# SPDX-License-Identifier: Apache-2.0
"""Retriever primitives."""

from cenote.retrievers.base import Retriever
from cenote.retrievers.vector import VectorRetriever

__all__ = ["Retriever", "VectorRetriever"]
