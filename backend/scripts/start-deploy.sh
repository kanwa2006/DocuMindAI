#!/bin/sh
set -e

echo "=== DocuMindAI Free-Tier Container Startup ==="

echo "1. Running database migrations..."
alembic upgrade head || echo "Migrations completed or already at head."

echo "2. Starting Celery background worker..."
celery -A app.workers.celery_app worker -Q main-queue,celery,export_queue,ocr_gpu_queue --concurrency=1 --loglevel=info &

echo "3. Starting Uvicorn API server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
