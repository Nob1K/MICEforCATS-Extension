#!/usr/bin/env bash
# Pull notebooks from Drive, then commit any changes.
# Usage: ./update.sh                       # pull everything in files.json
#        ./update.sh MICE-Evals.ipynb      # pull a subset
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"

"$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/pull_all.py" "$@"

cd "$REPO_ROOT"
git add original_files

if git diff --cached --quiet; then
    echo "No changes to commit."
    exit 0
fi

git commit -m "ran the update script"
