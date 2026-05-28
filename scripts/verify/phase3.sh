#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Manual end-to-end checks for Phase 3 (docs maturity: DoD + ADRs in nav).

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

check_dod_doc_exists() {
    info "Check 1/5: Definition of Done page exists with expected sections"
    local f="docs/site/dod.md"
    [[ -f "$f" ]] || { fail "$f missing"; return 0; }
    local sections
    sections=$(grep -c "^## " "$f" || true)
    if [[ "$sections" -ge 6 ]]; then
        pass "DoD page has $sections H2 sections (Code quality, API, Tests, Docs, Deps, Release, ...)"
    else
        fail "DoD page has only $sections H2 sections (expected >= 6)"
    fi
}

check_adrs_index_page_exists() {
    info "Check 2/5: ADRs index page lists all 8 ADRs"
    local f="docs/site/adrs.md"
    [[ -f "$f" ]] || { fail "$f missing"; return 0; }
    local count
    count=$(grep -cE "0[0-9]{3}-[a-z-]+\.md" "$f" || true)
    if [[ "$count" -ge 8 ]]; then
        pass "ADRs index references $count ADRs (expected >= 8)"
    else
        fail "ADRs index only references $count ADRs (expected >= 8)"
    fi
}

check_mkdocs_nav_has_new_pages() {
    info "Check 3/5: mkdocs.yml nav includes ADRs and Definition of Done entries"
    local missing=""
    grep -q "^  - ADRs:" mkdocs.yml || missing="${missing}ADRs "
    grep -q "^  - Definition of Done:" mkdocs.yml || missing="${missing}DoD "
    if [[ -z "$missing" ]]; then
        pass "both ADRs and Definition of Done entries present in nav"
    else
        fail "missing from mkdocs nav: $missing"
    fi
}

check_mkdocs_build_strict() {
    info "Check 4/5: mkdocs build --strict succeeds (zero warnings)"
    if uv run mkdocs build --strict > /tmp/cenote-mkdocs.log 2>&1; then
        pass "mkdocs build clean ($(grep -E 'built in' /tmp/cenote-mkdocs.log | tail -1))"
    else
        fail "mkdocs build failed — see /tmp/cenote-mkdocs.log"
    fi
}

check_all_referenced_adrs_exist() {
    info "Check 5/5: every ADR linked from docs/site/adrs.md actually exists"
    local missing=0
    while IFS= read -r adr; do
        if [[ ! -f "docs/adrs/$adr" ]]; then
            echo "  missing: docs/adrs/$adr" >&2
            missing=$((missing + 1))
        fi
    done < <(grep -oE "0[0-9]{3}-[a-z-]+\.md" docs/site/adrs.md | sort -u)
    if [[ "$missing" -eq 0 ]]; then
        pass "all referenced ADR files exist in docs/adrs/"
    else
        fail "$missing referenced ADR files are missing"
    fi
}

main() {
    info "Phase 3 verification — $(date -u +%FT%TZ)"
    check_dod_doc_exists
    check_adrs_index_page_exists
    check_mkdocs_nav_has_new_pages
    check_mkdocs_build_strict
    check_all_referenced_adrs_exist
    echo
    if [[ "$FAILED" -eq 0 ]]; then
        echo -e "${GREEN}${BOLD}Phase 3 verification: ALL CHECKS PASSED${NC}"
    else
        echo -e "${RED}${BOLD}Phase 3 verification: $FAILED check(s) failed${NC}"
        exit 1
    fi
}

main "$@"
