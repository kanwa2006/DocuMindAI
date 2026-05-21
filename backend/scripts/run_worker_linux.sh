#!/usr/bin/env bash
# Launch the Celery worker on Linux (production-equivalent local dev).
#
# Default `prefork` pool uses POSIX fork() for concurrency — fine on
# Linux/macOS. On Windows use scripts/run_worker_windows.ps1 (solo pool)
# instead; Windows cannot spawn billiard prefork workers.
#
# Usage:
#   cd backend
#   ./scripts/run_worker_linux.sh
#
# Pass extra arguments through, e.g. ./scripts/run_worker_linux.sh -Q ocr_gpu_queue

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

if ! command -v celery >/dev/null 2>&1; then
  echo "celery not found on PATH. Activate the project virtualenv first." >&2
  exit 1
fi

# Beat-enabled prefork worker. -Q defaults to celery+main-queue; override via args.
exec celery -A app.workers.celery_app worker \
  --pool=prefork \
  --concurrency=2 \
  --loglevel=info \
  -B \
  -Q main-queue,celery \
  "$@"
