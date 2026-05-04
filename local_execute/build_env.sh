#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

VENV_DIR=".venv"
REQUIREMENTS="requirements.txt"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "Installing requirements..."
pip install --upgrade pip
pip install -r "$REQUIREMENTS"

echo "Registering ipython kernel..."
python -m ipykernel install --user --name mice-venv --display-name "MICE venv"