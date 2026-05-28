# Launch the Celery worker on Windows.
#
# Why: Celery's default `prefork` pool relies on POSIX fork() and the
# `billiard` package. On Windows it raises PermissionError [WinError 5]
# and OSError [WinError 6] when spawning child processes. The `solo` pool
# runs all tasks in a single thread of the parent process, which is the
# only reliable option for local Windows development.
#
# Production (Linux) workers should use `prefork` for concurrency — see
# scripts/run_worker_linux.sh. Do NOT use `solo` in production.
#
# Usage:
#   cd backend
#   .\scripts\run_worker_windows.ps1
#
# Optional: pass extra arguments to celery worker (e.g. -Q queue1,queue2).

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $projectRoot

if (-not (Get-Command celery -ErrorAction SilentlyContinue)) {
    Write-Error "celery not found on PATH. Activate the project virtualenv first (e.g. .\venv\Scripts\Activate.ps1)."
    exit 1
}

# Beat-enabled solo worker — single process, single thread, runs scheduled tasks too.
#
# PART 5 fix — disable the per-child task recycle. celery_app.conf sets
# `worker_max_tasks_per_child=50`, which on a solo Windows worker means
# the whole process restarts every 50 tasks. Every restart re-loads the
# BAAI/bge-m3 embedding model (~1.2 GB), making document extraction
# painfully slow on the 51st upload. `--max-tasks-per-child=0` disables
# the recycle so the model stays resident for the worker's lifetime.
# (celery_app.py itself is marked STABLE in CLAUDE.md — override at the
# CLI instead.)
& celery -A app.workers.celery_app worker --pool=solo --loglevel=info -B --max-tasks-per-child=0 @args
