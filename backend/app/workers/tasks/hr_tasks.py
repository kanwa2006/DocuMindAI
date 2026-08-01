"""HR resume processing (Celery).

P0-7, final module. This one hid better than the others and it is worth recording
why. It did not use `asyncio.run()`; it used:

    loop = asyncio.get_event_loop()
    loop.run_until_complete(...)

which REUSES a single loop per worker process instead of creating and destroying
one per task. Pooled asyncpg connections therefore stayed bound to a loop that
was still alive, so HR kept working — it is the one workspace verified end-to-end
(3 resumes ranked 95/50/15 with cited evidence and CSV export) — while
`legal_tasks`, which built a fresh loop per call, failed on roughly every second
task. Same architectural violation, opposite symptom, which is exactly why the
class guard checks for the async session rather than for a particular spelling of
the bug.

It was still fragile: `asyncio.get_event_loop()` is deprecated and no longer
creates a loop implicitly on newer Pythons, and keeping one long-lived loop alive
purely so a connection pool stays valid couples two things that should not be
coupled. Now `SyncSessionLocal`, with an isolated short-lived loop for the async
LLM calls only — the same shape as every other repaired task module.

No P0-8 work: this module already read real `DocumentChunk` text (it never
shipped placeholder content). No P0-9 work: the HR models are not `TenantScoped`
and `hr_job_roles` already carries `owner_id`. All existing behaviour is
preserved — chunk assembly under `MAX_RESUME_CHARS`, prompt-injection
sanitisation, idempotent candidate reuse, and the non-fatal embedding fallback.
"""
import asyncio
import logging
from uuid import UUID

from sqlalchemy.future import select

from app.db.session import SyncSessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.hr import CandidateProfile, JobMatch, JobRole
from app.schemas.hr import CandidateExtractionSchema, MatchAnalysisSchema
from app.services.llm_service import llm_service
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Maximum chars fed to the LLM for a single resume to stay within token limits
MAX_RESUME_CHARS = 8000


def _run_async(coro):
    """Run one async LLM call on an isolated event loop.

    Replaces the shared `asyncio.get_event_loop()` this module used to keep
    alive. Safe because the DB session is now sync, so no pooled DB connection
    is ever bound to one of these loops — that coupling was P0-7.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _assemble_resume_text(chunks) -> str:
    """Concatenate chunk text up to MAX_RESUME_CHARS, in chunk order."""
    parts: list[str] = []
    total = 0
    for c in chunks:
        text = (c.text_content or "").strip()
        if not text:
            continue
        if total + len(text) > MAX_RESUME_CHARS:
            parts.append(text[: MAX_RESUME_CHARS - total])
            break
        parts.append(text)
        total += len(text)
    return "\n".join(parts).strip()


def process_candidate(job_id: str, document_id: str, workspace_id: str) -> None:
    """Process a single resume against a job description."""
    job_uuid = UUID(job_id)
    doc_uuid = UUID(document_id)
    ws_uuid = UUID(workspace_id)

    db = SyncSessionLocal()
    try:
        job = db.execute(
            select(JobRole).where(JobRole.id == job_uuid, JobRole.workspace_id == ws_uuid)
        ).scalar_one_or_none()
        doc = db.execute(
            select(Document).where(
                Document.id == doc_uuid, Document.workspace_id == ws_uuid
            )
        ).scalar_one_or_none()

        if not job or not doc:
            logger.error("[HR Task] Job %s or Doc %s not found.", job_id, document_id)
            return

        chunks = (
            db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == doc_uuid)
                .order_by(DocumentChunk.chunk_index)
            )
            .scalars()
            .all()
        )
        if not chunks:
            # Document hasn't finished extraction/chunking yet — skip, don't guess.
            logger.warning(
                "[HR Task] No chunks found for document %s. Ensure the document has "
                "status=READY before calling process_resume_batch.",
                doc_uuid,
            )
            return

        resume_text = _assemble_resume_text(chunks)

        # ── PHASE 6: Prompt-Injection Defense ────────────────────────────────
        suspicious_patterns = [
            "ignore previous instructions",
            "system prompt",
            "you are an AI",
            "fit score of 100",
            "override instructions",
            "disregard the above",
        ]
        if any(p in resume_text.lower() for p in suspicious_patterns):
            logger.warning(
                "[Security] Prompt-injection detected in resume %s. Sanitizing.", doc_uuid
            )
            resume_text = (
                "SANITIZED: This resume contained content that attempted to manipulate "
                "the scoring system. Score strictly on verified factual history only."
            )

        # Idempotent processing — reuse an existing profile for this document.
        candidate = db.execute(
            select(CandidateProfile).where(CandidateProfile.document_id == doc_uuid)
        ).scalar_one_or_none()

        if candidate is None:
            try:
                parsed_candidate = _run_async(
                    llm_service.generate_json(
                        query="Extract candidate details from this resume.",
                        grounded_context=resume_text,
                        response_schema=CandidateExtractionSchema,
                    )
                )
                candidate = CandidateProfile(
                    workspace_id=ws_uuid,
                    document_id=doc_uuid,
                    name=parsed_candidate.name or "Unknown",
                    email=parsed_candidate.email,
                    phone=parsed_candidate.phone,
                    skills=parsed_candidate.skills,
                    experience_years=parsed_candidate.experience_years,
                    education=parsed_candidate.education,
                    extracted_data=parsed_candidate.model_dump(),
                )
                db.add(candidate)
                db.flush()

                # L-13: populate the profile embedding so /hr candidates search can
                # rank semantically (pgvector) instead of ILIKE. Failure is loud but
                # non-fatal — search falls back to ILIKE.
                try:
                    embed_text = (
                        f"{candidate.name} "
                        f"{', '.join(candidate.skills or [])} "
                        f"{resume_text[:1000]}"
                    )
                    candidate.embedding = _run_async(
                        llm_service.get_embedding(embed_text)
                    )
                except Exception as embed_exc:
                    logger.error(
                        "[HR Task] Candidate embedding failed for %s: %s",
                        doc_uuid,
                        embed_exc,
                    )
            except Exception as e:
                logger.error("[HR Task] LLM Parse Failed for %s: %s", doc_uuid, e)
                return

        # ── Match candidate against the JD ───────────────────────────────────
        try:
            jd_context = (
                f"Title: {job.title}\n"
                f"Description: {job.description}\n"
                f"Requirements: {job.requirements}"
            )
            match_analysis = _run_async(
                llm_service.generate_json(
                    query="Generate a strict ATS fit score for this candidate.",
                    grounded_context=(
                        f"CANDIDATE:\n{candidate.extracted_data}\n\nJD:\n{jd_context}"
                    ),
                    response_schema=MatchAnalysisSchema,
                )
            )

            job_match = JobMatch(
                workspace_id=ws_uuid,
                job_id=job_uuid,
                candidate_id=candidate.id,
                fit_score=match_analysis.fit_score,
                match_analysis=match_analysis.model_dump(),
                status="NEW",
            )
            db.add(job_match)
            db.commit()
            logger.info(
                "[HR Task] Processed match %s for %s (Score: %s)",
                job_match.id,
                candidate.name,
                match_analysis.fit_score,
            )
        except Exception as e:
            logger.error(
                "[HR Task] LLM Match Failed for %s against %s: %s", doc_uuid, job_uuid, e
            )
    finally:
        db.close()


@celery_app.task(
    name="app.workers.tasks.hr_tasks.process_resume_batch", bind=True, max_retries=3
)
def process_resume_batch(self, job_id: str, document_id: str, workspace_id: str):
    """Celery entry point for resume processing."""
    try:
        process_candidate(job_id, document_id, workspace_id)
    except Exception as exc:
        logger.error("Failed to process resume %s. Retrying...", document_id)
        self.retry(exc=exc, countdown=10)


@celery_app.task(name="app.workers.tasks.hr_tasks.flag_stale_reviews")
def flag_stale_reviews():
    """Scheduled daily sweep for stale candidate reviews — NOT IMPLEMENTED.

    Beat runs this every morning at 08:00. It has never done anything: the body
    was a single INFO log reading "Running daily sweep...", which in the logs is
    indistinguishable from a sweep that ran and found nothing.

    Logged at WARNING and stated plainly rather than raising, because this is
    beat-scheduled — raising would generate a daily error every morning for a
    capability nobody has asked for yet. The real implementation would query
    JobMatch for `updated_at < now() - 7 days` with status in (NEW, INTERVIEW)
    and notify the assigned owner.
    """
    logger.warning(
        "[Workflow Automation] flag_stale_reviews is scheduled but NOT IMPLEMENTED — "
        "no stale candidate reviews are being detected or reported."
    )
