#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

NOTEBOOK="run_judge.ipynb"
OUTPUT="output_judge.ipynb"

source .venv/bin/activate
papermill "$NOTEBOOK" "$OUTPUT" -k mice-venv
