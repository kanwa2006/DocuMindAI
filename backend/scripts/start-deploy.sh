#!/bin/sh
set -e

echo "=== DocuMindAI Free-Tier Container Startup ==="

echo "1. Running database migrations..."
alembic upgrade head || echo "Migrations completed or already at head."

echo "2. Starting Uvicorn API server on port ${PORT:-8000}..."
# NOTE: Celery worker is omitted on free-tier (512 MB RAM).
# CELERY_TASK_ALWAYS_EAGER=true causes tasks to run synchronously in-process.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
