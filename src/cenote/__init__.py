# SPDX-License-Identifier: Apache-2.0
"""cenote — production-grade agentic RAG primitives."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("pycenote")
except PackageNotFoundError:  # uninstalled (dev) checkout
    __version__ = "0.0.0+dev"

__all__ = ["__version__"]
