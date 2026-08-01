"""Research paper ingestion (Celery).

P0-7: used `AsyncSessionLocal` in a sync Celery task via `asyncio.run()`; a
pooled asyncpg connection from a previous event loop failed intermittently with
"got Future attached to a different loop". Now `SyncSessionLocal`.

P0-8: `raw_text` was hardcoded to "Simulated paper text for {filename}. We
demonstrate that X causes Y using method Z..." — every paper ingested produced
findings about that fake study. Now reads the document's real chunk text.

P0-9: rows carried only `workspace_id`, a category slug shared by every user.
`owner_id` is derived from the document being processed.

**The Validation Gateway is re-enabled.** It read:

    if finding.evidence_quote.lower() in raw_text.lower() or True:  # Simulated pass

`or True` made the anti-hallucination check pass unconditionally — every quote
was accepted, including invented ones, and the `else` branch that logs a reject
was unreachable. That was not arbitrary: with `raw_text` fabricated (P0-8), a
real quote could never match, so the check had to be defeated for the pipeline
to produce anything. Restoring real text is what makes the gateway viable, so
the two fixes had to land together. Comparison is whitespace-normalised because
extracted PDF text wraps lines mid-sentence and an exact substring match would
reject quotes that genuinely are present.
"""
import asyncio
import logging
import re
import uuid

from sqlalchemy.future import select

from app.core.tenant_scope import tenant_scope
from app.db.session import SyncSessionLocal
from app.models.document import Document
from app.models.research import ResearchFinding, ResearchPaper
from app.schemas.research import PaperExtractionSchema
from app.services.llm_service import llm_service
from app.workers.celery_app import celery_app
from app.workers.tasks._document_text import DocumentTextUnavailable, load_document_text

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run one async LLM call on an isolated event loop (see legal_tasks/P0-7)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _normalise(text: str) -> str:
    """Collapse whitespace and lowercase, for quote containment checks.

    Extracted PDF text wraps lines mid-sentence, so a quote the model copied
    faithfully can still fail a raw substring test purely on line breaks.
    """
    return re.sub(r"\s+", " ", text).strip().lower()


def _process_research_logic(
    document_id: uuid.UUID, workspace_id: uuid.UUID, project_id: uuid.UUID
) -> None:
    db = SyncSessionLocal()
    try:
        doc = db.execute(
            select(Document).where(Document.id == document_id)
        ).scalar_one_or_none()
        if not doc:
            logger.error("Document %s not found.", document_id)
            return

        owner_id = doc.owner_id  # P0-9: the document's owner is the tenant

        with tenant_scope(owner_id):
            # P0-8: the real paper, not a fabricated abstract.
            raw_text = load_document_text(db, document_id)
            logger.info(
                "Extracting research metadata from %s (%d chars)",
                document_id,
                len(raw_text),
            )

            extraction = _run_async(
                llm_service.generate_json(
                    query="Extract the academic paper metadata and key findings.",
                    grounded_context=raw_text,
                    response_schema=PaperExtractionSchema,
                )
            )

            # Validation Gateway — deterministic anti-hallucination check.
            # Python verifies every evidence quote actually appears in the source;
            # the model does not get to vouch for itself.
            haystack = _normalise(raw_text)
            valid_findings = []
            for finding in extraction.findings:
                if _normalise(finding.evidence_quote) in haystack:
                    valid_findings.append(finding)
                else:
                    logger.warning(
                        "Validation Gateway reject: evidence quote not present in "
                        "source document: %r",
                        finding.evidence_quote[:120],
                    )

            if extraction.findings and not valid_findings:
                logger.error(
                    "Validation Gateway: all %d findings rejected for document %s — "
                    "no grounded findings to persist.",
                    len(extraction.findings),
                    document_id,
                )
                return

            paper = ResearchPaper(
                workspace_id=workspace_id,
                owner_id=owner_id,
                project_id=project_id,
                document_id=document_id,
                title=extraction.title,
                authors=extraction.authors,
                abstract=extraction.abstract,
                published_year=extraction.published_year,
            )
            paper.embedding = _run_async(
                llm_service.get_embedding(f"{paper.title} {paper.abstract}")
            )
            db.add(paper)
            db.flush()

            for finding_data in valid_findings:
                finding = ResearchFinding(
                    workspace_id=workspace_id,
                    owner_id=owner_id,
                    paper_id=paper.id,
                    statement=finding_data.statement,
                    evidence_quote=finding_data.evidence_quote,
                    methodology=finding_data.methodology,
                )
                finding.embedding = _run_async(
                    llm_service.get_embedding(finding.statement)
                )
                db.add(finding)

            db.commit()
            logger.info(
                "Processed research document %s — %d/%d findings passed the gateway",
                document_id,
                len(valid_findings),
                len(extraction.findings),
            )
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.research_tasks.process_research_batch", bind=True)
def process_research_batch(self, document_id: str, workspace_id: str, project_id: str):
    """PHASE 1: ASYNC RESEARCH PIPELINE — paper ingestion and validation."""
    try:
        _process_research_logic(
            uuid.UUID(document_id), uuid.UUID(workspace_id), uuid.UUID(project_id)
        )
    except DocumentTextUnavailable:
        # Permanent — retrying cannot produce text extraction never made.
        logger.error("Document %s has no extractable text; not retrying.", document_id)
        raise
    except Exception as exc:
        logger.error("Failed to process research document %s. Retrying...", document_id)
        self.retry(exc=exc, countdown=10)
