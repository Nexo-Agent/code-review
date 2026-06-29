#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Validating Python execution contract schemas..."
cd "$ROOT/shared"
uv run pytest tests/test_execution_contracts.py -q

echo "Building Go operator..."
cd "$ROOT/operator"
make lint build
go test ./... -count=1

echo "Contract validation passed."
