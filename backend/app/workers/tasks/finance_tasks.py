"""Finance document processing (Celery).

Same three defects as legal_tasks.py, fixed the same way — see that module and
`_document_text.py` for the full rationale.

P0-7: used `AsyncSessionLocal` inside a sync Celery task via `asyncio.run()`,
so a pooled asyncpg connection from a previous event loop failed intermittently
with "got Future attached to a different loop". Now `SyncSessionLocal`.

P0-8: `extracted_text` was hardcoded to "Simulated invoice for {filename}.
Vendor: AWS. Total: $5050.00. Line 1: EC2 $5000. Line 2: Tax $50." — every
invoice in the product, regardless of what the user uploaded, was analysed as
that fake AWS bill. Now reads the document's real chunk text.

P0-9: rows carried only `workspace_id`, a category slug shared by every user.
`owner_id` is derived from the document being processed.

The deterministic math validation below is INTENTIONAL and load-bearing: the LLM
extracts fields, Python computes and checks every number. That is the
extract-then-compute invariant in CLAUDE.md and the reason figures here cannot
be hallucinated. Do not move that arithmetic into the prompt.
"""
import asyncio
import logging
import uuid

from sqlalchemy.future import select

from app.core.tenant_scope import tenant_scope
from app.db.session import SyncSessionLocal
from app.models.document import Document
from app.models.finance import AuditFinding, FinancialDocument, Transaction
from app.schemas.finance import InvoiceExtractionSchema
from app.services.llm_service import llm_service
from app.workers.celery_app import celery_app
from app.workers.tasks._document_text import DocumentTextUnavailable, load_document_text

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run one async LLM call from this sync task on an isolated event loop.

    Safe only because the DB session is sync — no pooled DB connection is ever
    bound to one of these short-lived loops. That binding was P0-7.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _process_finance_logic(document_id: uuid.UUID, workspace_id: uuid.UUID) -> None:
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
            # P0-8: the real uploaded invoice, not a fabricated AWS bill.
            extracted_text = load_document_text(db, document_id)
            logger.info(
                "Extracting financial data from %s (%d chars)",
                document_id,
                len(extracted_text),
            )

            extraction = _run_async(
                llm_service.generate_json(
                    query="Extract the financial details from this invoice document.",
                    grounded_context=extracted_text,
                    response_schema=InvoiceExtractionSchema,
                )
            )

            fin_doc = FinancialDocument(
                workspace_id=workspace_id,
                owner_id=owner_id,
                document_id=document_id,
                doc_type=extraction.doc_type,
                vendor_name=extraction.vendor_name,
                total_amount=extraction.total_amount,
                currency=extraction.currency,
                status="EXTRACTED",
                extracted_data=extraction.model_dump(),
            )
            db.add(fin_doc)
            db.flush()

            has_anomaly = False
            calculated_total = 0.0

            for item in extraction.line_items:
                txn = Transaction(
                    workspace_id=workspace_id,
                    owner_id=owner_id,
                    financial_doc_id=fin_doc.id,
                    description=item.description,
                    amount=item.amount,
                    currency=item.currency,
                    category=item.category,
                )
                txn.embedding = _run_async(
                    llm_service.get_embedding(
                        f"{item.description} {item.amount} {item.currency}"
                    )
                )
                db.add(txn)
                db.flush()

                calculated_total += float(item.amount)

                # Deterministic heuristic — Python decides, not the model.
                if item.amount > 10000:
                    audit = AuditFinding(
                        workspace_id=workspace_id,
                        owner_id=owner_id,
                        financial_doc_id=fin_doc.id,
                        transaction_id=txn.id,
                        finding_type="LIMIT_EXCEEDED",
                        severity="HIGH",
                        description=(
                            f"Transaction amount {item.amount} {item.currency} "
                            "exceeds threshold."
                        ),
                    )
                    db.add(audit)
                    has_anomaly = True
                    txn.is_anomaly = True
                    txn.anomaly_reason = audit.description

            # Extract-then-compute: never trust the model's arithmetic.
            # Verify sum(line_items) == printed_total in Python.
            printed_total = (
                float(extraction.total_amount) if extraction.total_amount else 0.0
            )
            if abs(calculated_total - printed_total) > 0.01:  # float rounding tolerance
                db.add(
                    AuditFinding(
                        workspace_id=workspace_id,
                        owner_id=owner_id,
                        financial_doc_id=fin_doc.id,
                        finding_type="MATH_MISMATCH",
                        severity="HIGH",
                        description=(
                            f"Mathematical Mismatch: Sum of line items "
                            f"(${calculated_total:.2f}) does not match printed total "
                            f"(${printed_total:.2f}). Possible hallucination or fraud."
                        ),
                    )
                )
                has_anomaly = True

            if has_anomaly:
                fin_doc.status = "ANOMALY"

            db.commit()
            logger.info("Successfully processed financial document %s", fin_doc.id)
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.finance_tasks.process_finance_batch", bind=True)
def process_finance_batch(self, document_id: str, workspace_id: str):
    """PHASE 1: ASYNC FINANCE PROCESSING — offloads extraction and audit to Celery."""
    try:
        _process_finance_logic(uuid.UUID(document_id), uuid.UUID(workspace_id))
    except DocumentTextUnavailable:
        # Permanent condition — retrying cannot produce text extraction never made.
        logger.error("Document %s has no extractable text; not retrying.", document_id)
        raise
    except Exception as exc:
        logger.error("Failed to process finance document %s. Retrying...", document_id)
        self.retry(exc=exc, countdown=10)
