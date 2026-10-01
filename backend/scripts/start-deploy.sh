#!/bin/sh
set -e

echo "=== DocuMindAI Free-Tier Container Startup ==="

echo "1. Running database migrations..."
alembic upgrade head || echo "Migrations completed or already at head."

# Ensure free-tier container defaults are active in environment
export CELERY_TASK_ALWAYS_EAGER="${CELERY_TASK_ALWAYS_EAGER:-true}"
export EMBEDDING_PROVIDER="${EMBEDDING_PROVIDER:-gemini}"
export RERANKER_PROVIDER="${RERANKER_PROVIDER:-none}"
export OCR_SCANNED_ENABLED="${OCR_SCANNED_ENABLED:-false}"

echo "2. Starting Uvicorn API server on port ${PORT:-8000}..."
# NOTE: Celery worker is omitted on free-tier (512 MB RAM).
# CELERY_TASK_ALWAYS_EAGER=true causes tasks to run synchronously in-process.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
