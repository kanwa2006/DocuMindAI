import logging
from app.workers.celery_app import celery_app
from app.services.email_service import (
    send_welcome_email,
    send_trial_nudge_email,
    send_upgrade_reminder_email,
)

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.tasks.email_tasks.task_send_welcome_email",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def task_send_welcome_email(self, user_email: str, user_name: str = None) -> None:
    try:
        send_welcome_email(user_email, user_name)
    except Exception as exc:
        logger.error("[email_tasks] welcome email failed for %s: %s", user_email, exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.tasks.email_tasks.task_send_trial_nudge_email",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def task_send_trial_nudge_email(
    self, user_email: str, user_name: str = None, queries_used: int = 3
) -> None:
    try:
        send_trial_nudge_email(user_email, user_name, queries_used)
    except Exception as exc:
        logger.error("[email_tasks] trial nudge email failed for %s: %s", user_email, exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.tasks.email_tasks.task_send_upgrade_reminder_email",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def task_send_upgrade_reminder_email(self, user_email: str, user_name: str = None) -> None:
    try:
        send_upgrade_reminder_email(user_email, user_name)
    except Exception as exc:
        logger.error("[email_tasks] upgrade reminder email failed for %s: %s", user_email, exc)
        raise self.retry(exc=exc)
