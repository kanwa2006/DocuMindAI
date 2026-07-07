import asyncio
import uuid
import logging
from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.finance import FinancialDocument, Transaction, AuditFinding
from app.models.document import Document
from app.schemas.finance import InvoiceExtractionSchema
from app.services.llm_service import llm_service
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

async def _process_finance_logic(document_id: uuid.UUID, workspace_id: uuid.UUID):
    async with AsyncSessionLocal() as db:
        doc = (await db.execute(select(Document).where(Document.id == document_id))).scalar_one_or_none()
        if not doc:
            logger.error(f"Document {document_id} not found.")
            return

        # PHASE 2 & 3: Simulate Table Extraction
        logger.info(f"Extracting tables from {document_id}")
        extracted_text = f"Simulated invoice for {doc.filename}. Vendor: AWS. Total: $5050.00. Line 1: EC2 $5000. Line 2: Tax $50."
        
        # Security: Prompt Injection Defense
        if "ignore previous instructions" in extracted_text.lower():
            extracted_text = "SANITIZED: Prompt injection detected."

        extraction = await llm_service.generate_json(
            query="Extract the financial details from this invoice document.",
            grounded_context=extracted_text,
            response_schema=InvoiceExtractionSchema
        )
        
        fin_doc = FinancialDocument(
            workspace_id=workspace_id,
            document_id=document_id,
            doc_type=extraction.doc_type,
            vendor_name=extraction.vendor_name,
            total_amount=extraction.total_amount,
            currency=extraction.currency,
            status="EXTRACTED",
            extracted_data=extraction.model_dump()
        )
        db.add(fin_doc)
        await db.flush()

        has_anomaly = False
        calculated_total = 0.0
        
        # Process Line Items
        for item in extraction.line_items:
            txn = Transaction(
                workspace_id=workspace_id,
                financial_doc_id=fin_doc.id,
                description=item.description,
                amount=item.amount,
                currency=item.currency,
                category=item.category
            )
            
            # PHASE 4: Vector Generation for semantic search
            txn.embedding = await llm_service.get_embedding(f"{item.description} {item.amount} {item.currency}")
            
            db.add(txn)
            await db.flush()
            
            calculated_total += float(item.amount)
            
            # Simple heuristic audit check (Deterministic)
            if item.amount > 10000:
                audit = AuditFinding(
                    workspace_id=workspace_id,
                    financial_doc_id=fin_doc.id,
                    transaction_id=txn.id,
                    finding_type="LIMIT_EXCEEDED",
                    severity="HIGH",
                    description=f"Transaction amount {item.amount} {item.currency} exceeds threshold."
                )
                db.add(audit)
                has_anomaly = True
                txn.is_anomaly = True
                txn.anomaly_reason = audit.description

        # PHASE 3: Deterministic Math Validation
        # Never trust LLM calculations. Verify sum(line_items) == printed_total
        printed_total = float(extraction.total_amount) if extraction.total_amount else 0.0
        if abs(calculated_total - printed_total) > 0.01: # allow floating point rounding edge cases
            audit = AuditFinding(
                workspace_id=workspace_id,
                financial_doc_id=fin_doc.id,
                finding_type="MATH_MISMATCH",
                severity="HIGH",
                description=f"Mathematical Mismatch: Sum of line items (${calculated_total:.2f}) does not match printed total (${printed_total:.2f}). Possible hallucination or fraud."
            )
            db.add(audit)
            has_anomaly = True

        if has_anomaly:
            fin_doc.status = "ANOMALY"

        await db.commit()
        logger.info(f"Successfully processed financial document {fin_doc.id}")


@celery_app.task(name="app.workers.tasks.finance_tasks.process_finance_batch", bind=True)
def process_finance_batch(self, document_id: str, workspace_id: str):
    """
    PHASE 1: ASYNC FINANCE PROCESSING
    Offloads heavy table extraction and audit finding generation to Celery workers.
    """
    try:
        asyncio.run(_process_finance_logic(uuid.UUID(document_id), uuid.UUID(workspace_id)))
    except Exception as exc:
        logger.error(f"Failed to process finance document {document_id}. Retrying...")
        self.retry(exc=exc, countdown=10)
