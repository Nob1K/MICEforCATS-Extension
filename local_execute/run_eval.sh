#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

NOTEBOOK="MICE-Evals.ipynb"
OUTPUT="output_eval.ipynb"

source .venv/bin/activate
papermill "$NOTEBOOK" "$OUTPUT" -k mice-venv
