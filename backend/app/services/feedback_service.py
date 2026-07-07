import logging
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.models.correction import Correction, CorrectionNote
from app.models.eval_benchmark import EvalBenchmarkQuery

logger = logging.getLogger("audit.feedback")

# Only these issue types produce eval benchmark queries on approval
_EVAL_ELIGIBLE_TYPES = {"citation_wrong", "answer_incorrect", "hallucination"}


async def submit_correction(
    correction_data: dict,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Correction:
    """Create correction record. NEVER touches retrieval_service, chunks, or embeddings."""
    correction = Correction(**correction_data, user_id=user_id, status="pending")
    db.add(correction)
    await db.flush()
    logger.info(
        "[AUDIT] event=correction_submitted correction_id=%s user_id=%s issue_type=%s workspace=%s ts=%s",
        str(correction.id),
        str(user_id),
        correction.issue_type,
        correction.workspace_id,
        datetime.utcnow().isoformat(),
    )
    await db.commit()
    await db.refresh(correction)
    return correction


async def approve_correction(
    correction_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    db: AsyncSession,
) -> tuple[Correction, Optional[EvalBenchmarkQuery]]:
    """
    Approve correction and optionally promote it to an EvalBenchmarkQuery.
    Corrections NEVER modify production retrieval, chunks, or embeddings.
    Only evaluation datasets are updated — and only after human approval (this call).
    """
    correction = await db.get(Correction, correction_id)
    if correction is None:
        raise ValueError(f"Correction {correction_id} not found")

    correction.status = "approved"
    correction.reviewer_id = reviewer_id
    correction.reviewed_at = datetime.utcnow()

    eval_query: Optional[EvalBenchmarkQuery] = None
    if (
        correction.suggested_correction
        and correction.issue_type in _EVAL_ELIGIBLE_TYPES
        and correction.incorrect_excerpt
    ):
        eval_query = EvalBenchmarkQuery(
            workspace_id=correction.workspace_id,
            query_text=(
                f"[From correction {correction.id}]: "
                + correction.incorrect_excerpt[:300]
            ),
            query_type="human_reviewed",
            created_by=reviewer_id,
        )
        db.add(eval_query)
        correction.eval_query_created = True

    logger.info(
        "[AUDIT] event=correction_approved correction_id=%s reviewer_id=%s eval_created=%s ts=%s",
        str(correction_id),
        str(reviewer_id),
        correction.eval_query_created,
        datetime.utcnow().isoformat(),
    )
    await db.commit()
    await db.refresh(correction)
    return correction, eval_query


async def reject_correction(
    correction_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    note: Optional[str],
    db: AsyncSession,
) -> Correction:
    correction = await db.get(Correction, correction_id)
    if correction is None:
        raise ValueError(f"Correction {correction_id} not found")
    correction.status = "rejected"
    correction.reviewer_id = reviewer_id
    correction.reviewed_at = datetime.utcnow()
    if note:
        db.add(CorrectionNote(
            correction_id=correction_id,
            author_id=reviewer_id,
            note_text=note,
        ))
    await db.commit()
    await db.refresh(correction)
    return correction


async def escalate_correction(
    correction_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    db: AsyncSession,
) -> Correction:
    correction = await db.get(Correction, correction_id)
    if correction is None:
        raise ValueError(f"Correction {correction_id} not found")
    correction.status = "escalated"
    correction.reviewer_id = reviewer_id
    correction.reviewed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(correction)
    return correction


async def add_correction_note(
    correction_id: uuid.UUID,
    author_id: uuid.UUID,
    note_text: str,
    db: AsyncSession,
) -> CorrectionNote:
    note = CorrectionNote(
        correction_id=correction_id,
        author_id=author_id,
        note_text=note_text,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def detect_repeated_failures(
    workspace_id: str,
    db: AsyncSession,
) -> list[dict]:
    """Return issue types with >3 non-rejected corrections in the last 7 days."""
    result = await db.execute(
        text(
            """
            SELECT issue_type, COUNT(*) AS count
            FROM corrections
            WHERE workspace_id = :workspace_id
              AND status != 'rejected'
              AND created_at > NOW() - INTERVAL '7 days'
            GROUP BY issue_type
            HAVING COUNT(*) > 3
            ORDER BY count DESC
            """
        ),
        {"workspace_id": workspace_id},
    )
    return [{"issue_type": row.issue_type, "count": row.count} for row in result]


async def get_correction_trends(
    workspace_id: Optional[str],
    db: AsyncSession,
) -> list[dict]:
    """Correction counts by issue_type per week for last 8 weeks (for trend chart)."""
    params: dict = {}
    ws_clause = ""
    if workspace_id:
        ws_clause = "AND workspace_id = :workspace_id"
        params["workspace_id"] = workspace_id
    result = await db.execute(
        text(
            f"""
            SELECT
              DATE_TRUNC('week', created_at) AS week_start,
              issue_type,
              COUNT(*) AS count
            FROM corrections
            WHERE created_at > NOW() - INTERVAL '8 weeks'
            {ws_clause}
            GROUP BY DATE_TRUNC('week', created_at), issue_type
            ORDER BY week_start DESC
            """
        ),
        params,
    )
    return [
        {"week_start": str(row.week_start), "issue_type": row.issue_type, "count": row.count}
        for row in result
    ]
