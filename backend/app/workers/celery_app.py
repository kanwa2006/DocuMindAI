from celery import Celery
from app.core.config import settings
from app.core.telemetry import setup_telemetry

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.document_tasks",
        "app.workers.tasks.export_tasks",
        "app.workers.tasks.audio_tasks",
        "app.workers.tasks.ocr_tasks",
        "app.workers.tasks.hr_tasks"
    ]
)

# Phase 9: Performance + GPU Isolation
# Separate heavy multimodal tasks into dedicated queues so standard API responses aren't blocked
celery_app.conf.task_routes = {
    # Lightweight CPU parsing and generic workflow tasks
    "app.workers.tasks.hr_tasks.*": "main-queue",
    "app.workers.tasks.legal_tasks.*": "main-queue",
    "app.workers.tasks.finance_tasks.*": "main-queue",
    "app.workers.tasks.study_tasks.*": "main-queue",
    "app.workers.tasks.research_tasks.*": "main-queue",
    
    # PHASE 6: GPU WORKER ARCHITECTURE
    # Memory-safe batching queues for VRAM-intensive models
    "app.workers.tasks.ocr_tasks.*": "ocr_gpu_queue",
    "app.workers.tasks.embedding_tasks.*": "embedding_queue",
    "app.workers.tasks.retrieval_tasks.*": "retrieval_queue",
    "app.workers.tasks.export_tasks.*": "export_queue",
}

# PHASE 3: Hiring Workflow Automation
# Use Celery Beat for scheduled reminders and stale review flagging
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'flag-stale-hr-reviews-daily': {
        'task': 'app.workers.tasks.hr_tasks.flag_stale_reviews',
        'schedule': crontab(hour=8, minute=0), # Every morning at 8:00 AM
    },
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_max_tasks_per_child=50,
)

# Initialize Distributed Tracing for Celery Worker Threads
setup_telemetry(is_worker=True)
