#!/bin/bash
set -e

python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt

echo ""
echo "Running tests..."
python3 -m unittest discover -s tests -v
echo ""
echo "All tests passed. Starting app..."
python3 backup_gui.py
