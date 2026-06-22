#!/usr/bin/env bash
set -euo pipefail
echo "Starting Temporal Worker..."
python -m backend.temporal_worker.worker
