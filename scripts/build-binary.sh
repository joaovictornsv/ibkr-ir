#!/usr/bin/env bash
# Build a standalone ibkr-ir binary for the current OS/architecture.
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

.venv/bin/pip install -q -r requirements.txt pyinstaller
.venv/bin/pyinstaller --clean ibkr-ir.spec

echo ""
echo "Built: dist/ibkr-ir (or dist/ibkr-ir.exe on Windows)"
echo "Test:  dist/ibkr-ir --year 2025 --statement examples/sample_statement.csv"
