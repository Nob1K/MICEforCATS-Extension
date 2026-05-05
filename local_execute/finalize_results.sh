#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

NOTEBOOK="finalize_results.ipynb"
OUTPUT="output_finalize.ipynb"

source .venv/bin/activate
papermill "$NOTEBOOK" "$OUTPUT" -k mice-venv
