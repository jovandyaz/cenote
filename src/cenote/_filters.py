# SPDX-License-Identifier: Apache-2.0
"""Metadata filter helpers shared across stores and retrievers."""

from __future__ import annotations

from typing import Any


def matches_filter(metadata: dict[str, Any], filter: dict[str, Any]) -> bool:
    """Return True iff every (key, value) in `filter` exactly equals `metadata[key]`."""
    return all(metadata.get(key) == expected for key, expected in filter.items())
