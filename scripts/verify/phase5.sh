#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Manual end-to-end checks for Phase 5 (release automation + commit-msg lint + docs versioning).

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

check_release_please_manifest_matches_pyproject_version() {
    info "Check 1/5: release-please manifest version matches pyproject.toml"
    local manifest="$REPO_ROOT/.release-please-manifest.json"
    local config="$REPO_ROOT/release-please-config.json"
    local pyproject="$REPO_ROOT/pyproject.toml"

    if [[ ! -f "$manifest" ]]; then
        fail ".release-please-manifest.json not found"
        return
    fi
    if [[ ! -f "$config" ]]; then
        fail "release-please-config.json not found"
        return
    fi
    if ! uv run python -c "import json; json.load(open('$manifest'))" > /dev/null 2>&1; then
        fail ".release-please-manifest.json is not valid JSON"
        return
    fi
    if ! uv run python -c "import json; json.load(open('$config'))" > /dev/null 2>&1; then
        fail "release-please-config.json is not valid JSON"
        return
    fi

    local manifest_version pyproject_version
    manifest_version=$(uv run python -c "import json; d=json.load(open('$manifest')); print(next(iter(d.values())))" 2>/dev/null)
    pyproject_version=$(uv run python -c "import tomllib; d=tomllib.load(open('$pyproject','rb')); print(d['project']['version'])" 2>/dev/null)

    if [[ -n "$manifest_version" && "$manifest_version" == "$pyproject_version" ]]; then
        pass "manifest version ($manifest_version) matches pyproject ($pyproject_version)"
    else
        fail "version mismatch: manifest=$manifest_version pyproject=$pyproject_version"
    fi
}

check_release_please_workflow_pins_v5() {
    info "Check 2/5: release-please workflow pins googleapis/release-please-action@v5"
    local wf="$REPO_ROOT/.github/workflows/release-please.yml"

    if [[ ! -f "$wf" ]]; then
        fail "$wf not found"
        return
    fi
    if ! uv run python -c "import yaml; yaml.safe_load(open('$wf'))" > /dev/null 2>&1; then
        fail "release-please.yml is not valid YAML"
        return
    fi
    if grep -E "uses:\s*googleapis/release-please-action@v5" "$wf" > /dev/null 2>&1; then
        local pinned
        pinned=$(grep -E "uses:\s*googleapis/release-please-action@v5" "$wf" | head -1 | sed 's/^[[:space:]]*//')
        pass "workflow pins v5 — $pinned"
    else
        fail "release-please.yml does NOT pin googleapis/release-please-action@v5*"
    fi
}

check_gitlint_hook_installed_in_pre_commit_and_git() {
    info "Check 3/5: gitlint registered in .pre-commit-config.yaml + commit-msg hook installed"
    local precommit="$REPO_ROOT/.pre-commit-config.yaml"
    local commit_msg_hook="$REPO_ROOT/.git/hooks/commit-msg"
    local gitlint_cfg="$REPO_ROOT/.gitlint"

    if [[ ! -f "$precommit" ]]; then
        fail "$precommit not found"
        return
    fi
    local mentions
    mentions=$(grep -c "gitlint" "$precommit" || true)
    if [[ "$mentions" -lt 2 ]]; then
        fail "gitlint mentions in .pre-commit-config.yaml = $mentions (expected >= 2: repo URL + hook id)"
        return
    fi
    if [[ ! -f "$commit_msg_hook" ]]; then
        fail ".git/hooks/commit-msg NOT installed — run 'uv run pre-commit install --hook-type commit-msg'"
        return
    fi
    if [[ ! -f "$gitlint_cfg" ]]; then
        fail ".gitlint config file not found"
        return
    fi
    pass "gitlint hook registered (mentions=$mentions), commit-msg hook installed, .gitlint present"
}

check_gitlint_accepts_project_commit_styles() {
    info "Check 4/5: gitlint accepts/rejects expected commit message styles"
    local should_pass=(
        "chore(verify): test scoped"
        "fix(compose): test scoped"
        "feat: test unscoped"
        "docs(adrs): test scoped"
    )
    local should_fail=(
        "BAD MESSAGE NO PREFIX"
        "wip: skip this"
    )

    local local_failed=0

    for msg in "${should_pass[@]}"; do
        if echo "$msg" | uv run gitlint > /dev/null 2>&1; then
            pass "accepted: '$msg'"
        else
            fail "should ACCEPT but rejected: '$msg'"
            local_failed=$((local_failed + 1))
        fi
    done

    for msg in "${should_fail[@]}"; do
        if echo "$msg" | uv run gitlint > /dev/null 2>&1; then
            fail "should REJECT but accepted: '$msg'"
            local_failed=$((local_failed + 1))
        else
            pass "rejected: '$msg'"
        fi
    done

    if [[ "$local_failed" -eq 0 ]]; then
        pass "gitlint regex correctly classifies all 6 fixtures"
    else
        warn "gitlint misclassified $local_failed message(s) — check .gitlint regex"
    fi
}

check_mike_dev_dep_installed() {
    info "Check 5/5: mike installed as dev dep + docs/operations.md present"
    if ! uv run mike --version > /dev/null 2>&1; then
        fail "'uv run mike --version' failed — mike not installed in venv"
        return
    fi
    local mike_version
    mike_version=$(uv run mike --version 2>&1 | head -1)

    if ! grep -A20 "^\[dependency-groups\]" "$REPO_ROOT/pyproject.toml" \
            | grep -E '"mike>=2\.2' > /dev/null 2>&1; then
        fail "pyproject.toml [dependency-groups].dev does NOT pin mike>=2.2"
        return
    fi

    local ops_doc="$REPO_ROOT/docs/operations.md"
    if [[ ! -f "$ops_doc" ]]; then
        fail "docs/operations.md not found"
        return
    fi
    local h2_count
    h2_count=$(grep -c "^## " "$ops_doc" || true)
    if [[ "$h2_count" -lt 5 ]]; then
        fail "docs/operations.md has $h2_count H2 sections (expected >= 5)"
        return
    fi
    pass "mike installed ($mike_version), pinned >=2.2, operations.md has $h2_count H2 sections"
}

main() {
    info "Phase 5 verification — $(date -u +%FT%TZ)"
    check_release_please_manifest_matches_pyproject_version
    check_release_please_workflow_pins_v5
    check_gitlint_hook_installed_in_pre_commit_and_git
    check_gitlint_accepts_project_commit_styles
    check_mike_dev_dep_installed
    echo
    if [[ "$FAILED" -eq 0 ]]; then
        echo -e "${GREEN}${BOLD}Phase 5 verification: ALL CHECKS PASSED${NC}"
    else
        echo -e "${RED}${BOLD}Phase 5 verification: $FAILED check(s) failed${NC}"
        exit 1
    fi
}

main "$@"
