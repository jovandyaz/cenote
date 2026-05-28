#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Manual end-to-end checks for Phase 1 (security maturity: SAST + SCA + signing + SBOM).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

export PATH="/Users/jovandyaz/Library/Python/3.9/bin:$PATH"

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

check_codeql_workflow_valid() {
    info "Check 1/6: CodeQL workflow exists, parses, uses security-and-quality queries"
    local wf=".github/workflows/codeql.yml"
    [[ -f "$wf" ]] || { fail "$wf missing"; return 0; }
    uv run python -c "import yaml; yaml.safe_load(open('$wf'))" > /dev/null 2>&1 \
        || { fail "$wf invalid YAML"; return 0; }
    if grep -q 'queries: security-and-quality' "$wf"; then
        pass "CodeQL workflow valid + uses security-and-quality query suite"
    else
        fail "CodeQL workflow missing security-and-quality query suite"
    fi
}

check_osv_scanner_workflows_valid() {
    info "Check 2/6: OSV-Scanner PR + scheduled workflows exist and use reusable pattern"
    local pr=".github/workflows/osv-scanner-pr.yml"
    local sched=".github/workflows/osv-scanner-scheduled.yml"
    [[ -f "$pr" ]] || { fail "$pr missing"; return 0; }
    [[ -f "$sched" ]] || { fail "$sched missing"; return 0; }
    uv run python -c "import yaml; yaml.safe_load(open('$pr')); yaml.safe_load(open('$sched'))" \
            > /dev/null 2>&1 \
        || { fail "OSV-Scanner workflows invalid YAML"; return 0; }
    if grep -q 'osv-scanner-reusable-pr.yml' "$pr" && grep -q 'osv-scanner-reusable.yml' "$sched"; then
        pass "both OSV-Scanner workflows use the official reusable pattern"
    else
        fail "OSV-Scanner workflows do not reference the reusable workflows"
    fi
}

check_release_workflow_has_sbom() {
    info "Check 3/6: release.yml generates and uploads SBOM"
    local wf=".github/workflows/release.yml"
    [[ -f "$wf" ]] || { fail "$wf missing"; return 0; }
    uv run python -c "import yaml; yaml.safe_load(open('$wf'))" > /dev/null 2>&1 \
        || { fail "$wf invalid YAML"; return 0; }
    local has_gen has_upload
    has_gen=$(grep -c 'generate_sbom.sh' "$wf" || true)
    has_upload=$(grep -c 'action-gh-release' "$wf" || true)
    if [[ "$has_gen" -ge 1 && "$has_upload" -ge 1 ]]; then
        pass "release.yml runs generate_sbom.sh and attaches via action-gh-release"
    else
        fail "release.yml missing SBOM gen or upload (gen=$has_gen upload=$has_upload)"
    fi
}

check_pinned_action_versions_are_current() {
    info "Check 4/6: pinned GitHub Action versions are reachable (latest releases sane)"
    if ! command -v gh > /dev/null 2>&1; then
        warn "gh CLI not in PATH — skipping action-version sanity check"
        return 0
    fi
    local osv_latest
    osv_latest="$(gh api repos/google/osv-scanner-action/releases --jq '.[0].tag_name' 2>/dev/null || true)"
    local osv_pinned
    osv_pinned="$(grep -oE 'osv-scanner-action/.github/workflows/[^@]+@[^"]+' \
        .github/workflows/osv-scanner-*.yml 2>/dev/null | head -1 | sed 's/.*@//')"
    if [[ -n "$osv_latest" && -n "$osv_pinned" ]]; then
        if [[ "$osv_pinned" == "$osv_latest" ]]; then
            pass "OSV-Scanner pinned to latest stable ($osv_pinned)"
        else
            warn "OSV-Scanner pinned to $osv_pinned; latest is $osv_latest (Dependabot will bump)"
        fi
    else
        warn "could not resolve OSV-Scanner pin/release for comparison"
    fi
}

check_local_osv_scanner_if_available() {
    info "Check 5/6: local osv-scanner runs clean (skipped if not installed)"
    if ! command -v osv-scanner > /dev/null 2>&1; then
        warn "osv-scanner not installed (install: brew install osv-scanner) — skipping"
        return 0
    fi
    if osv-scanner scan source --recursive --skip-git . > /tmp/osv-scan.log 2>&1; then
        pass "local osv-scanner: no vulnerabilities found"
    else
        warn "local osv-scanner reported findings — review /tmp/osv-scan.log"
    fi
}

check_sbom_still_generates() {
    info "Check 6/6: SBOM script still works end-to-end"
    if ./scripts/generate_sbom.sh > /dev/null 2>&1 && [[ -f sbom.cdx.json ]]; then
        local fmt
        fmt="$(python3 -c 'import json; print(json.load(open("sbom.cdx.json"))["bomFormat"])' 2>/dev/null || true)"
        rm -f sbom.cdx.json
        if [[ "$fmt" == "CycloneDX" ]]; then
            pass "SBOM regenerated successfully (CycloneDX)"
        else
            fail "SBOM regenerated but bomFormat is '$fmt'"
        fi
    else
        fail "scripts/generate_sbom.sh did not produce sbom.cdx.json"
    fi
}

main() {
    info "Phase 1 verification — $(date -u +%FT%TZ)"
    check_codeql_workflow_valid
    check_osv_scanner_workflows_valid
    check_release_workflow_has_sbom
    check_pinned_action_versions_are_current
    check_local_osv_scanner_if_available
    check_sbom_still_generates
    echo
    if [[ "$FAILED" -eq 0 ]]; then
        echo -e "${GREEN}${BOLD}Phase 1 verification: ALL CHECKS PASSED${NC}"
    else
        echo -e "${RED}${BOLD}Phase 1 verification: $FAILED check(s) failed${NC}"
        exit 1
    fi
}

main "$@"
