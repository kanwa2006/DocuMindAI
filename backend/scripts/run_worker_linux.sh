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
#
# PART 5 — bump max-tasks-per-child so the BAAI/bge-m3 embedding model
# (~1.2 GB) stays resident across many uploads. Default 50 in celery_app.conf
# caused full process restarts (and model re-downloads/re-loads) every 50
# tasks. 1000 is large enough for a day's work without forfeiting the
# safety net of an eventual recycle. celery_app.py itself is STABLE per
# CLAUDE.md — override at the CLI here instead.
exec celery -A app.workers.celery_app worker \
  --pool=prefork \
  --concurrency=2 \
  --loglevel=info \
  --max-tasks-per-child=1000 \
  -B \
  -Q main-queue,celery \
  "$@"
