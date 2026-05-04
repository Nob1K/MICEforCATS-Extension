#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

NOTEBOOK="MICE-Replica_feat_extract.ipynb"
OUTPUT="output_feat_extract.ipynb"

source .venv/bin/activate
papermill "$NOTEBOOK" "$OUTPUT" -k mice-venv