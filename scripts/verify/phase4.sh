#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Manual end-to-end checks for Phase 4 (tech debt + bug fixes + new primitives).

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

check_new_runtime_deps_importable() {
    info "Check 1/8: stamina + aiolimiter importable from runtime venv"
    if uv run python -c "import stamina, aiolimiter; print(f'stamina={stamina.__version__} aiolimiter={aiolimiter.__version__}')" > /tmp/cenote-deps.log 2>&1; then
        pass "$(cat /tmp/cenote-deps.log)"
    else
        fail "stamina or aiolimiter import failed — see /tmp/cenote-deps.log"
    fi
}

check_retrying_uses_stamina() {
    info "Check 2/8: _http.py retrying() uses stamina.retry_context"
    if grep -q "stamina.retry_context" src/cenote/embedders/_http.py; then
        pass "stamina.retry_context found in _http.py"
    else
        fail "stamina.retry_context NOT found in _http.py — refactor may have regressed"
    fi
}

check_ratelimiter_uses_aiolimiter() {
    info "Check 3/8: RateLimiter wraps aiolimiter.AsyncLimiter"
    if grep -q "AsyncLimiter" src/cenote/embedders/_http.py; then
        pass "AsyncLimiter found in _http.py"
    else
        fail "AsyncLimiter NOT found in _http.py — refactor may have regressed"
    fi
}

check_hnsw_search_in_transaction() {
    info "Check 4/8: pgvector search() wraps SET LOCAL in conn.transaction()"
    if grep -A2 "async with self._pool.acquire" src/cenote/stores/pgvector.py \
            | grep -q "conn.transaction()"; then
        pass "search() acquires connection within a transaction"
    else
        fail "search() does NOT wrap in transaction — SET LOCAL bug may have regressed"
    fi
}

check_hybrid_returns_exceptions() {
    info "Check 5/8: HybridRetriever gathers with return_exceptions=True"
    if grep -q "return_exceptions=True" src/cenote/retrievers/hybrid.py; then
        pass "return_exceptions=True present in HybridRetriever"
    else
        fail "return_exceptions=True missing — resilience fix may have regressed"
    fi
}

check_bm25_has_lru_and_invalidate() {
    info "Check 6/8: BM25Retriever has max_cached_namespaces + invalidate()"
    local has_lru has_invalidate
    has_lru=$(grep -c "max_cached_namespaces" src/cenote/retrievers/bm25.py || true)
    has_invalidate=$(grep -c "def invalidate" src/cenote/retrievers/bm25.py || true)
    if [[ "$has_lru" -ge 1 && "$has_invalidate" -ge 1 ]]; then
        pass "BM25 has LRU cap + invalidate() (mentions=$has_lru, invalidate=$has_invalidate)"
    else
        fail "BM25 missing LRU or invalidate (lru=$has_lru, invalidate=$has_invalidate)"
    fi
}

check_new_primitives_importable() {
    info "Check 7/8: TracedVectorStore + IndexingPipeline importable"
    if uv run python -c "from cenote.observability.wrappers import TracedVectorStore; from cenote.pipeline import IndexingPipeline, IndexingProgress; print('ok')" > /dev/null 2>&1; then
        pass "TracedVectorStore + IndexingPipeline import cleanly"
    else
        fail "new primitives failed to import — check src/cenote/{observability,pipeline}/"
    fi
}

check_full_suite_passes_at_threshold() {
    info "Check 8/8: full unit suite passes at coverage threshold"
    if uv run pytest -m "not integration" --cov=cenote --cov-fail-under=85 \
            --quiet --no-header > /tmp/cenote-phase4.log 2>&1; then
        pass "$(tail -1 /tmp/cenote-phase4.log)"
    else
        fail "unit suite or coverage failed — see /tmp/cenote-phase4.log"
    fi
}

main() {
    info "Phase 4 verification — $(date -u +%FT%TZ)"
    check_new_runtime_deps_importable
    check_retrying_uses_stamina
    check_ratelimiter_uses_aiolimiter
    check_hnsw_search_in_transaction
    check_hybrid_returns_exceptions
    check_bm25_has_lru_and_invalidate
    check_new_primitives_importable
    check_full_suite_passes_at_threshold
    echo
    if [[ "$FAILED" -eq 0 ]]; then
        echo -e "${GREEN}${BOLD}Phase 4 verification: ALL CHECKS PASSED${NC}"
    else
        echo -e "${RED}${BOLD}Phase 4 verification: $FAILED check(s) failed${NC}"
        exit 1
    fi
}

main "$@"
