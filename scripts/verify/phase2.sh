#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Manual end-to-end checks for Phase 2 (testing quality: hypothesis + benchmarks + coverage ratchet).

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

check_hypothesis_installed() {
    info "Check 1/5: hypothesis + pytest-benchmark are available"
    if uv run python -c "import hypothesis, pytest_benchmark" > /dev/null 2>&1; then
        local ver
        ver=$(uv run python -c "import hypothesis, pytest_benchmark; print(f'hypothesis={hypothesis.__version__} pytest-benchmark={pytest_benchmark.__version__}')" 2>/dev/null)
        pass "$ver"
    else
        fail "hypothesis or pytest-benchmark not importable"
    fi
}

check_property_tests_pass() {
    info "Check 2/5: property tests run and pass with default hypothesis settings"
    if uv run pytest tests/chunkers/test_recursive.py tests/retrievers/test_hybrid.py \
            tests/tokenizers/test_spanish.py --quiet > /tmp/cenote-prop.log 2>&1; then
        pass "property tests pass ($(tail -1 /tmp/cenote-prop.log))"
    else
        fail "property tests failed or errored — see /tmp/cenote-prop.log"
    fi
}

check_benchmarks_execute() {
    info "Check 3/5: 3 benchmarks execute without error"
    if uv run pytest tests/benchmarks/ --benchmark-only --benchmark-disable-gc \
            --quiet > /tmp/cenote-bench.log 2>&1; then
        pass "all 3 benchmarks completed ($(grep -E '^=+.*passed' /tmp/cenote-bench.log | tail -1))"
    else
        fail "benchmarks failed — see /tmp/cenote-bench.log"
    fi
}

check_benchmarks_skipped_by_default() {
    info "Check 4/5: benchmarks are skipped by default in normal pytest runs"
    if uv run pytest tests/benchmarks/ --quiet > /tmp/cenote-skip.log 2>&1 \
            && grep -q "Skipping benchmark" /tmp/cenote-skip.log; then
        pass "benchmarks correctly skipped by default (--benchmark-skip in addopts)"
    else
        fail "benchmarks did NOT skip by default — addopts may be wrong"
    fi
}

check_coverage_threshold_85() {
    info "Check 5/5: coverage threshold ratcheted to 85% still passes"
    if uv run pytest -m "not integration" --cov=cenote --cov-fail-under=85 \
            --quiet --no-header > /dev/null 2>&1; then
        pass "pytest passes at --cov-fail-under=85 (current ratchet)"
    else
        fail "coverage dropped below 85% — investigate"
    fi
}

main() {
    info "Phase 2 verification — $(date -u +%FT%TZ)"
    check_hypothesis_installed
    check_property_tests_pass
    check_benchmarks_execute
    check_benchmarks_skipped_by_default
    check_coverage_threshold_85
    echo
    if [[ "$FAILED" -eq 0 ]]; then
        echo -e "${GREEN}${BOLD}Phase 2 verification: ALL CHECKS PASSED${NC}"
    else
        echo -e "${RED}${BOLD}Phase 2 verification: $FAILED check(s) failed${NC}"
        exit 1
    fi
}

main "$@"
