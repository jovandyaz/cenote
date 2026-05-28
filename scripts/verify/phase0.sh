#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Manual end-to-end checks for Phase 0 (security + tooling baseline).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if ! command -v uv > /dev/null 2>&1; then
    echo "ERROR: 'uv' not found in PATH. Install via https://docs.astral.sh/uv/ then retry." >&2
    exit 127
fi

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; FAILED=$((FAILED + 1)); }
info() { echo -e "${BOLD}--- $1${NC}"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

FAILED=0

check_coverage_threshold_enforces() {
    info "Check 1/5: coverage threshold actually fails CI on regression"
    if uv run pytest -m "not integration" --cov=cenote --cov-fail-under=99 \
            --quiet --no-header > /dev/null 2>&1; then
        fail "pytest passed at --cov-fail-under=99 (expected fail since baseline ~90%)"
    else
        pass "pytest correctly fails when threshold > baseline"
    fi
    if uv run pytest -m "not integration" --cov=cenote --cov-fail-under=80 \
            --quiet --no-header > /dev/null 2>&1; then
        pass "pytest passes at --cov-fail-under=80 (current threshold)"
    else
        fail "pytest fails at --cov-fail-under=80 — coverage dropped below 80%"
    fi
}

check_ruff_s_catches_new_violations() {
    info "Check 2/5: ruff S rule catches new pseudo-random crypto patterns"
    local output
    output="$(echo 'import random; secret = random.random()' \
        | uv run ruff check --stdin-filename foo.py --select S - 2>&1 || true)"
    if echo "$output" | grep -q S311; then
        pass "ruff S311 raised on bare random.random()"
    else
        fail "ruff did not flag random.random() — S rule may be disabled"
    fi
}

check_docker_digest_resolves() {
    info "Check 3/5: pinned Docker digest is reachable"
    if ! command -v docker > /dev/null 2>&1; then
        warn "docker not in PATH — skipping (CI will validate)"
        return 0
    fi
    local digest_line
    digest_line="$(grep -E 'pgvector/pgvector@sha256:' docker-compose.test.yml | head -1)"
    if [[ -z "$digest_line" ]]; then
        fail "no digest pin found in docker-compose.test.yml"
        return 0
    fi
    if docker buildx imagetools inspect "$(echo "$digest_line" | sed -E 's/.*(pgvector\/pgvector@sha256:[a-f0-9]+).*/\1/')" > /dev/null 2>&1; then
        pass "digest resolves on Docker registry"
    else
        warn "digest did not resolve — check network or registry rate limit"
    fi
}

check_sbom_generates_valid_cyclonedx() {
    info "Check 4/5: SBOM script produces valid CycloneDX JSON"
    if ! ./scripts/generate_sbom.sh > /dev/null 2>&1; then
        fail "scripts/generate_sbom.sh exited non-zero"
        return 0
    fi
    if [[ ! -f sbom.cdx.json ]]; then
        fail "sbom.cdx.json was not produced"
        return 0
    fi
    local fmt
    fmt="$(python3 -c 'import json; print(json.load(open("sbom.cdx.json"))["bomFormat"])' 2>/dev/null || true)"
    local count
    count="$(python3 -c 'import json; print(len(json.load(open("sbom.cdx.json")).get("components", [])))' 2>/dev/null || echo 0)"
    if [[ "$fmt" == "CycloneDX" && "$count" -gt 0 ]]; then
        pass "SBOM valid: bomFormat=CycloneDX, components=$count"
    else
        fail "SBOM invalid: bomFormat=$fmt, components=$count"
    fi
    rm -f sbom.cdx.json
}

check_readme_has_not_use_section() {
    info "Check 5/5: README contains 'When NOT to use cenote' section"
    if grep -q '^## When NOT to use cenote' README.md; then
        pass "section found in README.md"
    else
        fail "section not found — README.md may have been reverted"
    fi
}

main() {
    info "Phase 0 verification — $(date -u +%FT%TZ)"
    check_coverage_threshold_enforces
    check_ruff_s_catches_new_violations
    check_docker_digest_resolves
    check_sbom_generates_valid_cyclonedx
    check_readme_has_not_use_section
    echo
    if [[ "$FAILED" -eq 0 ]]; then
        echo -e "${GREEN}${BOLD}Phase 0 verification: ALL CHECKS PASSED${NC}"
    else
        echo -e "${RED}${BOLD}Phase 0 verification: $FAILED check(s) failed${NC}"
        exit 1
    fi
}

main "$@"
