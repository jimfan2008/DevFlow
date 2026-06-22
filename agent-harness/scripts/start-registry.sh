#!/usr/bin/env bash
set -euo pipefail
echo "Starting Agent Registry API..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
