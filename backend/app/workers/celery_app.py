from celery import Celery
from celery.signals import worker_process_init
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
        "app.workers.tasks.hr_tasks",
        # C-2 fix — these modules were routed in task_routes and dispatched by
        # the legal/finance/study/research /process endpoints but never
        # imported by the worker, so their tasks were unregistered and never
        # ran. (email_tasks stays unregistered: email is sent synchronously
        # via email_service; the module is dead code pending its own issue.)
        "app.workers.tasks.legal_tasks",
        "app.workers.tasks.finance_tasks",
        "app.workers.tasks.study_tasks",
        "app.workers.tasks.research_tasks",
        # Phase 20 — automation tasks
        "app.automation.auto_health_check",
        "app.automation.auto_key_rotation",
        "app.automation.auto_daily_digest",
        "app.automation.auto_db_cleanup",
        "app.automation.auto_subscription_check",
        "app.automation.auto_gst_notice",
        "app.automation.auto_model_check",
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
    # Memory-safe batching queues for VRAM-intensive models.
    # H-3 fix: these queues MUST be consumed by a running worker (-Q). The
    # default deployment runs a single worker consuming
    # main-queue,celery,export_queue,ocr_gpu_queue; a dedicated GPU worker
    # may take over ocr_gpu_queue later without changing these routes.
    # (Phantom routes for nonexistent embedding_tasks/retrieval_tasks
    # modules were removed — do not re-add a route without a real module.)
    "app.workers.tasks.ocr_tasks.*": "ocr_gpu_queue",
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
    # Phase 20 — Automation scripts
    'auto-health-check': {
        'task': 'app.automation.auto_health_check.run_health_check',
        'schedule': crontab(minute='*/5'),
    },
    'auto-key-rotation-check': {
        'task': 'app.automation.auto_key_rotation.check_api_keys',
        'schedule': crontab(minute=0),
    },
    'auto-daily-digest': {
        'task': 'app.automation.auto_daily_digest.send_daily_digest',
        'schedule': crontab(hour=2, minute=30),
    },
    'auto-db-cleanup': {
        'task': 'app.automation.auto_db_cleanup.run_db_cleanup',
        'schedule': crontab(hour=20, minute=30, day_of_week=6),
    },
    'auto-subscription-check': {
        'task': 'app.automation.auto_subscription_check.run_subscription_check',
        'schedule': crontab(hour=18, minute=30),
    },
    'auto-gst-notice': {
        'task': 'app.automation.auto_gst_notice.check_gst_rates',
        'schedule': crontab(hour=3, minute=30, day_of_week=1),
    },
    'auto-model-check': {
        'task': 'app.automation.auto_model_check.check_model_status',
        'schedule': crontab(hour=4, minute=30, day_of_week=1),
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


@worker_process_init.connect
def _dispose_inherited_db_pool(**_kwargs):
    """
    P0-5: drop the SQLAlchemy pool inherited from the Celery parent.

    `app.db.session` builds `sync_engine` at import time, which happens in the
    parent process. Every prefork child is fork()ed from that parent and
    therefore inherits its pool — including any live TCP sockets in it. Two
    processes writing to one socket interleave their traffic and corrupt the
    wire protocol, which surfaces as spurious "server closed the connection
    unexpectedly" / "prepared statement does not exist" errors that look like
    database faults rather than fork faults.

    `worker_max_tasks_per_child=50` makes this recurring, not one-off: every
    child recycle forks a fresh child off the same parent.

    close=False is REQUIRED, not an optimisation. The default close=True would
    close the inherited connections — but those file descriptors are shared
    with the parent, so closing them here severs connections the parent still
    believes it owns. close=False abandons the pool's references without
    touching the sockets, letting the child open its own connections lazily.
    """
    from app.db.session import sync_engine

    sync_engine.dispose(close=False)

# Initialize Distributed Tracing for Celery Worker Threads
setup_telemetry(is_worker=True)
