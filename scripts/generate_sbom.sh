#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Generate CycloneDX SBOM from the uv-managed virtual environment.
# Output: sbom.cdx.json in the repo root.

set -euo pipefail

uv run cyclonedx-py environment \
    --output-format JSON \
    --output-file sbom.cdx.json \
    --pyproject pyproject.toml \
    "$(uv run python -c 'import sys; print(sys.executable)')"

echo "SBOM written to sbom.cdx.json"
