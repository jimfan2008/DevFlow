#!/usr/bin/env bash
set -euo pipefail
echo "Running all tests..."
uv run pytest tests/ -v --cov=backend --cov-report=term-missing
