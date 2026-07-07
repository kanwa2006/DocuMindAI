import logging
import asyncio
from typing import Dict, Any
from uuid import UUID
from app.db.session import AsyncSessionLocal
from app.workers.celery_app import celery_app
from app.models.hr import JobRole, CandidateProfile, JobMatch
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.schemas.hr import CandidateExtractionSchema, MatchAnalysisSchema
from app.services.llm_service import llm_service
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

# Maximum chars fed to the LLM for a single resume to stay within token limits
MAX_RESUME_CHARS = 8000

async def process_candidate_async(job_id: str, document_id: str, workspace_id: str):
    """
    Processes a single resume against a JD asynchronously.
    Fetches real DocumentChunk rows; falls back gracefully when none exist yet.
    """
    job_uuid = UUID(job_id)
    doc_uuid = UUID(document_id)
    ws_uuid = UUID(workspace_id)

    async with AsyncSessionLocal() as db:
        # Verify Job and Document exist and belong to this workspace
        job = (await db.execute(
            select(JobRole).where(JobRole.id == job_uuid, JobRole.workspace_id == ws_uuid)
        )).scalar_one_or_none()
        doc = (await db.execute(
            select(Document).where(Document.id == doc_uuid, Document.workspace_id == ws_uuid)
        )).scalar_one_or_none()

        if not job or not doc:
            logger.error(f"[HR Task] Job {job_id} or Doc {document_id} not found.")
            return

        # ── Fetch real resume text from DocumentChunk rows ────────────────────
        chunk_result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc_uuid)
            .order_by(DocumentChunk.chunk_index)
        )
        chunks = chunk_result.scalars().all()

        if chunks:
            # Concatenate chunk text up to MAX_RESUME_CHARS
            parts = []
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
            resume_text = "\n".join(parts).strip()
        else:
            # Document hasn't finished OCR/chunking yet — log and skip
            logger.warning(
                f"[HR Task] No chunks found for document {doc_uuid}. "
                "Ensure the document has status=READY before calling process_resume_batch."
            )
            return

        # ── PHASE 6: Prompt-Injection Defense ────────────────────────────────
        suspicious_patterns = [
            "ignore previous instructions",
            "system prompt",
            "you are an AI",
            "fit score of 100",
            "override instructions",
            "disregard the above",
        ]
        is_suspicious = any(p in resume_text.lower() for p in suspicious_patterns)
        if is_suspicious:
            logger.warning(f"[Security] Prompt-injection detected in resume {doc_uuid}. Sanitizing.")
            resume_text = (
                "SANITIZED: This resume contained content that attempted to manipulate "
                "the scoring system. Score strictly on verified factual history only."
            )

        # Check for existing CandidateProfile (idempotent processing)
        existing_candidate = (await db.execute(
            select(CandidateProfile).where(CandidateProfile.document_id == doc_uuid)
        )).scalar_one_or_none()

        if existing_candidate:
            candidate = existing_candidate
        else:
            try:
                parsed_candidate = await llm_service.generate_json(
                    query="Extract candidate details from this resume.",
                    grounded_context=resume_text,
                    response_schema=CandidateExtractionSchema,
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
                await db.flush()
            except Exception as e:
                logger.error(f"[HR Task] LLM Parse Failed for {doc_uuid}: {e}")
                return

        # ── Match candidate against the JD ───────────────────────────────────
        try:
            jd_context = (
                f"Title: {job.title}\n"
                f"Description: {job.description}\n"
                f"Requirements: {job.requirements}"
            )
            match_analysis = await llm_service.generate_json(
                query="Generate a strict ATS fit score for this candidate.",
                grounded_context=(
                    f"CANDIDATE:\n{candidate.extracted_data}\n\nJD:\n{jd_context}"
                ),
                response_schema=MatchAnalysisSchema,
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
            await db.commit()
            logger.info(
                f"[HR Task] Processed match {job_match.id} for "
                f"{candidate.name} (Score: {match_analysis.fit_score})"
            )
        except Exception as e:
            logger.error(f"[HR Task] LLM Match Failed for {doc_uuid} against {job_uuid}: {e}")


@celery_app.task(name="app.workers.tasks.hr_tasks.process_resume_batch", bind=True, max_retries=3)
def process_resume_batch(self, job_id: str, document_id: str, workspace_id: str):
    """Celery wrapper for async resume processing."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(process_candidate_async(job_id, document_id, workspace_id))
    except Exception as exc:
        logger.error(f"Failed to process resume {document_id}. Retrying...")
        self.retry(exc=exc, countdown=10)


@celery_app.task(name="app.workers.tasks.hr_tasks.flag_stale_reviews")
def flag_stale_reviews():
    """
    Scheduled daily task — finds candidates stuck in 'NEW' or 'INTERVIEW'
    for more than 7 days and logs them for recruiter notification.
    """
    logger.info("[Workflow Automation] Running daily sweep for stale candidate reviews...")
    # Full implementation would query JobMatch for updated_at < now - 7 days
    # and dispatch email/app notifications to the assigned owner_id.
