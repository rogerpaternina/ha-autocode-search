#!/usr/bin/env bash
# Run pytest with coverage and generate HTML and terminal reports.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m coverage erase
python3 -m coverage run -m pytest "$@"
python3 -m coverage report
python3 -m coverage html
echo "HTML coverage report: ${ROOT}/htmlcov/index.html"
