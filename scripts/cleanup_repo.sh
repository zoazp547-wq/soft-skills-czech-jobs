#!/usr/bin/env bash
# =============================================================================
# Cleanup script — prepares the project for publication on GitHub.
#
# Run this ONCE on a fresh copy of the project, BEFORE `git init`.
# It deletes:
#   - macOS junk (.DS_Store, ._* files)
#   - Python bytecode caches (__pycache__/, *.pyc)
#   - log files (logs/, *.log)
#   - private data (raw scraped JSONs)
#   - duplicate output folder (outputOld/)
#   - personal AI assistant config (.claude/ — leaks $USER path)
#
# Usage:
#   ./scripts/cleanup_repo.sh          # interactive (asks before deleting)
#   ./scripts/cleanup_repo.sh --yes    # non-interactive
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

YES=0
if [[ "${1:-}" == "--yes" ]] || [[ "${1:-}" == "-y" ]]; then
    YES=1
fi

confirm() {
    if [[ $YES -eq 1 ]]; then
        return 0
    fi
    read -r -p "  $1 [y/N] " reply
    [[ "$reply" =~ ^[Yy]$ ]]
}

section() {
    echo
    echo "=== $1 ==="
}

remove_if_exists() {
    local target="$1"
    if [[ -e "$target" ]]; then
        echo "  removing: $target ($(du -sh "$target" 2>/dev/null | cut -f1))"
        rm -rf "$target"
    fi
}

# -----------------------------------------------------------------------------
section "macOS junk"
# -----------------------------------------------------------------------------
mac_count=$(find . -name ".DS_Store" -o -name "._*" 2>/dev/null | wc -l)
if [[ $mac_count -gt 0 ]]; then
    echo "  found $mac_count macOS metadata files"
    if confirm "  Delete?"; then
        find . -name ".DS_Store" -delete 2>/dev/null
        find . -name "._*" -delete 2>/dev/null
        echo "  ✓ removed"
    fi
else
    echo "  ✓ none found"
fi

# -----------------------------------------------------------------------------
section "Python bytecode caches"
# -----------------------------------------------------------------------------
pyc_count=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
if [[ $pyc_count -gt 0 ]]; then
    echo "  found $pyc_count __pycache__ directories"
    if confirm "  Delete?"; then
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete 2>/dev/null || true
        echo "  ✓ removed"
    fi
else
    echo "  ✓ none found"
fi

# -----------------------------------------------------------------------------
section "Log files"
# -----------------------------------------------------------------------------
if [[ -d "logs" ]]; then
    echo "  found logs/ ($(du -sh logs | cut -f1))"
    if confirm "  Delete?"; then
        rm -rf logs/
        echo "  ✓ removed"
    fi
fi

# -----------------------------------------------------------------------------
section "Private scraped data (Jobs.cz copyright + GDPR)"
# -----------------------------------------------------------------------------
private_files=(
    "output/jobs_cz_administrativa.json"
    "output/jobs_cz_administrativa_clean.json"
    "output/jobs_cz_administrativa_nlp.json"
)
found=0
for f in "${private_files[@]}"; do
    if [[ -f "$f" ]]; then
        found=1
        echo "  found: $f ($(du -sh "$f" | cut -f1))"
    fi
done
if [[ $found -eq 1 ]]; then
    echo "  ⚠  These files contain full ad descriptions and employer names."
    echo "  ⚠  They MUST NOT be published on GitHub."
    if confirm "  Delete?"; then
        for f in "${private_files[@]}"; do
            remove_if_exists "$f"
        done
        echo "  ✓ removed"
    fi
fi

# -----------------------------------------------------------------------------
section "Duplicate output folder"
# -----------------------------------------------------------------------------
if [[ -d "outputOld" ]]; then
    echo "  found outputOld/ ($(du -sh outputOld | cut -f1)) — appears to be a duplicate"
    if confirm "  Delete?"; then
        rm -rf outputOld/
        echo "  ✓ removed"
    fi
fi

# -----------------------------------------------------------------------------
section "Personal AI assistant config"
# -----------------------------------------------------------------------------
if [[ -d ".claude" ]]; then
    echo "  found .claude/ — likely contains absolute paths with your username"
    if [[ -f ".claude/settings.local.json" ]]; then
        if grep -q '/Users/\|/home/' .claude/settings.local.json 2>/dev/null; then
            echo "  ⚠  Confirmed: file contains user-path references."
        fi
    fi
    if confirm "  Delete?"; then
        rm -rf .claude/
        echo "  ✓ removed"
    fi
fi

# -----------------------------------------------------------------------------
section "Summary"
# -----------------------------------------------------------------------------
echo "  Repository state after cleanup:"
echo
du -sh ./* 2>/dev/null | sort -h
echo
echo "  Total: $(du -sh . | cut -f1)"
echo
echo "Next steps:"
echo "  1. Verify no sensitive files remain:"
echo "     find . -type f \\( -name '*.json' -o -name '*.log' \\) -not -path './output/tfidf_analysis/*'"
echo "  2. Initialize git:"
echo "     git init && git add . && git status"
echo "  3. Review what 'git status' shows BEFORE first commit."
echo "  4. First commit:"
echo "     git commit -m 'Initial public release accompanying bachelor thesis'"
