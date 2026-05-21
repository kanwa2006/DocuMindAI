import glob as glob_module
import logging
import os
from datetime import datetime, timedelta

import redis as redis_lib
from celery import shared_task
from sqlalchemy import delete as sql_delete, text

from app.core.config import settings
from app.db.session import SyncSessionLocal, sync_engine
from app.models.document import Document, DocumentStatus

logger = logging.getLogger(__name__)

_redis = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


@shared_task(name="app.automation.auto_db_cleanup.run_db_cleanup")
def run_db_cleanup():
    summary = {}
    now = datetime.utcnow()

    # 1. Delete temp upload files older than 7 days
    try:
        files_deleted = 0
        bytes_freed = 0
        cutoff_7d = now - timedelta(days=7)
        storage = settings.STORAGE_PATH
        if os.path.exists(storage):
            for fpath in glob_module.glob(os.path.join(storage, "**", "*"), recursive=True):
                if not os.path.isfile(fpath):
                    continue
                mtime = datetime.utcfromtimestamp(os.path.getmtime(fpath))
                if mtime < cutoff_7d:
                    try:
                        size = os.path.getsize(fpath)
                        os.remove(fpath)
                        files_deleted += 1
                        bytes_freed += size
                    except OSError:
                        pass
        summary["temp_files"] = (
            f"Deleted {files_deleted} files, freed {bytes_freed / (1024 * 1024):.1f} MB"
        )
    except Exception as exc:
        summary["temp_files"] = f"Error: {exc}"
        logger.error("[db_cleanup] temp files error: %s", exc)

    # 2. Delete Document records with status=FAILED older than 30 days
    try:
        cutoff_30d = now - timedelta(days=30)
        with SyncSessionLocal() as db:
            result = db.execute(
                sql_delete(Document).where(
                    Document.status == DocumentStatus.FAILED,
                    Document.created_at < cutoff_30d,
                )
            )
            deleted_docs = result.rowcount
            db.commit()
        summary["failed_docs"] = f"Deleted {deleted_docs} failed document records"
    except Exception as exc:
        summary["failed_docs"] = f"Error: {exc}"
        logger.error("[db_cleanup] failed docs error: %s", exc)

    # 3. Delete stale OTP keys from Redis (keys with no TTL — never expired)
    try:
        otp_deleted = 0
        for pattern in ("email_otp:*", "phone_otp:*"):
            cursor = 0
            while True:
                cursor, keys = _redis.scan(cursor, match=pattern, count=100)
                for key in keys:
                    if _redis.ttl(key) == -1:
                        _redis.delete(key)
                        otp_deleted += 1
                if cursor == 0:
                    break
        summary["otp_keys"] = f"Deleted {otp_deleted} stale OTP keys"
    except Exception as exc:
        summary["otp_keys"] = f"Error: {exc}"
        logger.error("[db_cleanup] OTP cleanup error: %s", exc)

    # 4. Delete stale Redis session keys (no TTL set)
    try:
        sessions_deleted = 0
        cursor = 0
        while True:
            cursor, keys = _redis.scan(cursor, match="session:*", count=100)
            for key in keys:
                if _redis.ttl(key) == -1:
                    _redis.delete(key)
                    sessions_deleted += 1
            if cursor == 0:
                break
        summary["sessions"] = f"Deleted {sessions_deleted} stale session keys"
    except Exception as exc:
        summary["sessions"] = f"Error: {exc}"
        logger.error("[db_cleanup] session cleanup error: %s", exc)

    # 5. VACUUM ANALYZE — must run in autocommit mode (cannot be inside a transaction)
    try:
        with sync_engine.connect() as conn:
            auto_conn = conn.execution_options(isolation_level="AUTOCOMMIT")
            for table in ("documents", "chat_sessions"):
                try:
                    auto_conn.execute(text(f"VACUUM ANALYZE {table}"))
                except Exception as te:
                    logger.warning("[db_cleanup] VACUUM %s skipped: %s", table, te)
            try:
                auto_conn.execute(text("VACUUM ANALYZE token_usage"))
            except Exception:
                pass  # table may not exist in all deployments
        summary["vacuum"] = "VACUUM ANALYZE completed on documents, chat_sessions"
    except Exception as exc:
        summary["vacuum"] = f"Error: {exc}"
        logger.error("[db_cleanup] VACUUM error: %s", exc)

    lines = " | ".join(f"{k}: {v}" for k, v in summary.items())
    logger.info("[db_cleanup] Cleanup complete — %s", lines)
