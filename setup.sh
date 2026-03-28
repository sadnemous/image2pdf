#!/usr/bin/env bash
set -e
python -m venv venv
. venv/bin/activate
pip install -r requirement.txt

echo "Setup complete. Activate with: . venv/bin/activate"