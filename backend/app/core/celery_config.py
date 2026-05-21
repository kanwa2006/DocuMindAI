from celery.schedules import crontab

# Phase 20 — Automation beat schedule entries
# These are merged into celery_app.conf.beat_schedule in celery_app.py.
AUTOMATION_BEAT_SCHEDULE = {
    # Script 1: Health check every 5 minutes
    "auto-health-check": {
        "task": "app.automation.auto_health_check.run_health_check",
        "schedule": crontab(minute="*/5"),
    },
    # Script 2: API key rotation check — top of every hour
    "auto-key-rotation-check": {
        "task": "app.automation.auto_key_rotation.check_api_keys",
        "schedule": crontab(minute=0),
    },
    # Script 3: Daily digest — 8:00 AM IST (02:30 UTC)
    "auto-daily-digest": {
        "task": "app.automation.auto_daily_digest.send_daily_digest",
        "schedule": crontab(hour=2, minute=30),
    },
    # Script 4: DB cleanup — Sunday 2:00 AM IST (Saturday 20:30 UTC)
    "auto-db-cleanup": {
        "task": "app.automation.auto_db_cleanup.run_db_cleanup",
        "schedule": crontab(hour=20, minute=30, day_of_week=6),
    },
    # Script 5: Subscription check — midnight IST (18:30 UTC)
    "auto-subscription-check": {
        "task": "app.automation.auto_subscription_check.run_subscription_check",
        "schedule": crontab(hour=18, minute=30),
    },
    # Script 6: GST rate notice — Monday 9:00 AM IST (03:30 UTC)
    "auto-gst-notice": {
        "task": "app.automation.auto_gst_notice.check_gst_rates",
        "schedule": crontab(hour=3, minute=30, day_of_week=1),
    },
    # Script 7: Model deprecation check — Monday 10:00 AM IST (04:30 UTC)
    "auto-model-check": {
        "task": "app.automation.auto_model_check.check_model_status",
        "schedule": crontab(hour=4, minute=30, day_of_week=1),
    },
}
