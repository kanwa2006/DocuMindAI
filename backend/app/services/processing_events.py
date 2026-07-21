"""M-1: real SSE progress streams for workspace processing.

Replaces the fake `progress: i*10` heartbeat generators in the five
`/events/*` endpoints. Progress is derived from actual persisted state:

- legal/finance/study/research: the tracked Document's status transitions
  (QUEUED → PROCESSING → EXTRACTED → READY/FAILED), polled with a fresh
  short-lived session per tick (an SSE stream must not pin a pooled
  connection for minutes).
- HR: the number of JobMatch rows produced for the job, completing once
  the count is non-zero and stable.

The emitted `progress` values are monotonic stage markers, not fabricated
percentages — the pipeline does not report finer granularity.
"""
import asyncio
import json
import logging
import uuid as uuid_module
from typing import AsyncGenerator

from sqlalchemy import select, func

from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

POLL_INTERVAL_SEC = 2.0
MAX_POLLS = 150  # ~5 minutes — matches the frontend document-polling timeout

# Stage markers for real Document.status values.
_STATUS_PROGRESS = {
    "QUEUED": 10,
    "PROCESSING": 50,
    "EXTRACTED": 80,
    "READY": 100,
    "FAILED": 100,
}


def _frame(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def document_status_event_stream(
    document_id, owner_id, id_field: str = "document_id"
) -> AsyncGenerator[str, None]:
    """Stream real Document.status transitions until READY/FAILED/timeout."""
    from app.models.document import Document

    doc_uuid = uuid_module.UUID(str(document_id))
    owner_uuid = uuid_module.UUID(str(owner_id))
    last_status = None

    for _ in range(MAX_POLLS):
        async with AsyncSessionLocal() as db:
            doc = (await db.execute(
                select(Document).where(
                    Document.id == doc_uuid, Document.owner_id == owner_uuid
                )
            )).scalar_one_or_none()

        if doc is None:
            yield _frame({"status": "not_found", id_field: str(document_id)})
            return

        status = str(getattr(doc.status, "value", doc.status)).upper()
        if status != last_status:
            last_status = status
            if status == "READY":
                yield _frame({"status": "complete", "progress": 100,
                              id_field: str(document_id)})
                return
            if status == "FAILED":
                yield _frame({"status": "failed", id_field: str(document_id)})
                return
            yield _frame({
                "status": "processing",
                "progress": _STATUS_PROGRESS.get(status, 10),
                "stage": status.lower(),
                id_field: str(document_id),
            })
        await asyncio.sleep(POLL_INTERVAL_SEC)

    yield _frame({"status": "timeout", id_field: str(document_id)})


async def hr_job_candidates_event_stream(
    job_id, workspace_id
) -> AsyncGenerator[str, None]:
    """Stream the real number of processed candidates for a job; complete
    when the count is non-zero and stable for three polls."""
    from app.models.hr import JobMatch

    job_uuid = uuid_module.UUID(str(job_id))
    last_count = -1
    stable_polls = 0

    for _ in range(MAX_POLLS):
        async with AsyncSessionLocal() as db:
            count = (await db.execute(
                select(func.count()).select_from(JobMatch).where(
                    JobMatch.job_id == job_uuid,
                    JobMatch.workspace_id == workspace_id,
                )
            )).scalar() or 0

        if count != last_count:
            last_count = count
            stable_polls = 0
            yield _frame({"status": "processing", "candidates_processed": count,
                          "job_id": str(job_id)})
        else:
            stable_polls += 1
            if count > 0 and stable_polls >= 3:
                yield _frame({"status": "complete", "candidates_processed": count,
                              "job_id": str(job_id)})
                return
        await asyncio.sleep(POLL_INTERVAL_SEC)

    yield _frame({"status": "timeout", "job_id": str(job_id)})
