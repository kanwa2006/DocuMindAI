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
& celery -A app.workers.celery_app worker --pool=solo --loglevel=info -B @args
