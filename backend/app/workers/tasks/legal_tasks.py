"""Legal contract processing (Celery).

Three defects were fixed here together because they are the same lines of code:

P0-7 — this module used `AsyncSessionLocal` inside a sync Celery task via
`asyncio.run()`. Every call creates a NEW event loop, so a pooled asyncpg
connection created under a previous loop fails with
`RuntimeError: got Future attached to a different loop` — intermittently, on
roughly every second task. `CLAUDE.md` states the invariant plainly: FastAPI +
asyncpg on the request path, Celery + `SyncSessionLocal` (psycopg2) on the
worker path, never mixed. `document_tasks.py` was already correct; this now
matches it, including its pattern of an isolated event loop for the async LLM
calls only (the DB never crosses a loop boundary because it is no longer async).

P0-8 — `contract_text` was a HARDCODED string ("Simulated text. 1.
Confidentiality... 2. Liability capped at $50."). The uploaded document was
fetched only for its filename and its actual text was never read, so every
contract in the product produced the same two fabricated clauses. The Risk
Report was therefore analysing a contract nobody uploaded. Real chunk text is
now used, and an empty extraction fails LOUDLY rather than silently analysing
nothing — `CLAUDE.md`'s "loud degradation" invariant.

P0-9 — rows were written with only `workspace_id`, which is a category slug
shared by every user. `owner_id` is now derived from the document being
processed: the document's owner IS the tenant. Deriving it rather than passing
it as a task argument means a caller cannot supply a mismatched owner, and the
task signature stays stable.
"""
import asyncio
import logging
import uuid

from sqlalchemy.future import select

from app.core.tenant_scope import tenant_scope
from app.db.session import SyncSessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.legal import Contract, Clause, ComplianceRule, RedlineSuggestion
from app.schemas.legal import ContractSegmentationSchema, ClauseComplianceSchema
from app.services.llm_service import llm_service
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


class ContractTextUnavailable(RuntimeError):
    """The document produced no extractable text.

    Raised instead of falling back to placeholder text: a Risk Report built on
    text we do not have is worse than no Risk Report, because it looks correct.
    """


def _run_async(coro):
    """Run one async call from this sync task on an isolated event loop.

    Same approach as `document_tasks.generate_proactive_insights_task`:
    `asyncio.run()` raises if a loop is already running in the worker thread,
    so a fresh loop is created and explicitly closed. Safe here precisely
    because the database session is sync — no pooled DB connection is ever
    bound to one of these short-lived loops (that was P0-7).
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _load_contract_text(db, document_id: uuid.UUID) -> str:
    """The document's real extracted text, in chunk order."""
    chunks = (
        db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        .scalars()
        .all()
    )
    text = "\n".join(c.text_content for c in chunks if c.text_content)
    if not text.strip():
        raise ContractTextUnavailable(
            f"Document {document_id} has no extracted text — cannot analyse a "
            "contract whose contents are unknown. Check extraction/OCR first."
        )
    return text


def _process_contract_logic(document_id: uuid.UUID, workspace_id: uuid.UUID) -> None:
    db = SyncSessionLocal()
    try:
        doc = db.execute(
            select(Document).where(Document.id == document_id)
        ).scalar_one_or_none()
        if not doc:
            logger.error("Document %s not found.", document_id)
            return

        # P0-9: the document's owner is the tenant. Derived, never passed in.
        owner_id = doc.owner_id

        with tenant_scope(owner_id):
            rules = (
                db.execute(
                    select(ComplianceRule).where(
                        ComplianceRule.workspace_id == workspace_id
                    )
                )
                .scalars()
                .all()
            )

            # P0-8: the real document, not a placeholder. Raises if empty.
            contract_text = _load_contract_text(db, document_id)

            contract = Contract(
                workspace_id=workspace_id,
                owner_id=owner_id,
                document_id=document_id,
                title=f"Contract: {doc.filename}",
                status="IN_REVIEW",
            )
            db.add(contract)
            db.flush()

            logger.info("Segmenting contract %s (%d chars)", contract.id, len(contract_text))
            segmentation = _run_async(
                llm_service.generate_json(
                    query="Segment this contract into individual clauses.",
                    grounded_context=contract_text,
                    response_schema=ContractSegmentationSchema,
                )
            )

            contract.party_name = segmentation.party_name
            contract.contract_type = segmentation.contract_type

            highest_risk = "LOW"

            for extracted_clause in segmentation.clauses:
                clause = Clause(
                    workspace_id=workspace_id,
                    owner_id=owner_id,
                    contract_id=contract.id,
                    section_name=extracted_clause.section_name,
                    original_text=extracted_clause.original_text,
                    clause_type=extracted_clause.clause_type,
                    risk_level="COMPLIANT",
                )
                clause.embedding = _run_async(
                    llm_service.get_embedding(clause.original_text)
                )
                db.add(clause)
                db.flush()

                for rule in rules:
                    if rule.category not in (clause.clause_type, "ALL"):
                        continue
                    evaluation = _run_async(
                        llm_service.generate_json(
                            query=(
                                "Evaluate this clause against the compliance rule: "
                                f"'{rule.rule_description}'."
                            ),
                            grounded_context=clause.original_text,
                            response_schema=ClauseComplianceSchema,
                        )
                    )
                    if evaluation.is_compliant:
                        continue

                    clause.risk_level = evaluation.risk_level
                    clause.compliance_notes = evaluation.compliance_notes
                    if evaluation.risk_level == "HIGH":
                        highest_risk = "HIGH"
                    elif evaluation.risk_level == "MEDIUM" and highest_risk == "LOW":
                        highest_risk = "MEDIUM"

                    if evaluation.needs_redline and evaluation.suggested_redline_text:
                        db.add(
                            RedlineSuggestion(
                                workspace_id=workspace_id,
                                owner_id=owner_id,
                                clause_id=clause.id,
                                rule_id=rule.id,
                                suggested_text=evaluation.suggested_redline_text,
                                explanation=evaluation.compliance_notes,
                            )
                        )

            contract.risk_score = highest_risk
            contract.status = "REVIEW_REQUIRED" if highest_risk == "HIGH" else "APPROVED"
            db.commit()
            logger.info("Successfully processed contract %s", contract.id)
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.legal_tasks.process_contract_batch", bind=True)
def process_contract_batch(self, document_id: str, workspace_id: str):
    """PHASE 1: ASYNC LEGAL PROCESSING — offloads compliance work to Celery."""
    try:
        _process_contract_logic(uuid.UUID(document_id), uuid.UUID(workspace_id))
    except ContractTextUnavailable:
        # Retrying cannot conjure text that extraction never produced. Fail
        # visibly instead of burning the retry budget on a permanent condition.
        logger.error("Contract %s has no extractable text; not retrying.", document_id)
        raise
    except Exception as exc:
        logger.error("Failed to process contract %s. Retrying...", document_id)
        self.retry(exc=exc, countdown=10)
