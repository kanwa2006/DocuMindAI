from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Any
import uuid
import asyncio

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.finance import FinancialDocument, Transaction, AuditFinding, FinancialRule
from app.models.document import Document
from app.schemas.finance import FinancialDocumentResponse, AuditFindingResponse, InvoiceExtractionSchema, AnomalyDetectionSchema
from app.services.llm_service import llm_service
from app.workers.tasks.finance_tasks import process_finance_batch

router = APIRouter()

@router.post("/process")
async def process_financial_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 1: ASYNC FINANCE PROCESSING
    Offloads heavy table extraction and audit finding generation to Celery workers.
    """
    workspace_id = uuid.UUID(current_user["workspace_id"])
    doc = (await db.execute(select(Document).where(Document.id == document_id, Document.workspace_id == workspace_id))).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Dispatch to Celery
    process_finance_batch.delay(str(document_id), str(workspace_id))
    
    return {"status": "processing_queued", "document_id": str(document_id)}

@router.get("/events/finance/{document_id}")
async def sse_finance_processing_updates(
    document_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    """
    PHASE 1: Live Processing Updates
    Server-Sent Events (SSE) endpoint to push finance processing status.
    """
    async def event_generator():
        # Simulated heartbeat for SSE UI update
        for i in range(1, 10):
            await asyncio.sleep(2)
            yield f"data: {{\"status\": \"processing\", \"progress\": {i * 10}, \"document_id\": \"{document_id}\"}}\n\n"
        yield f"data: {{\"status\": \"complete\", \"document_id\": \"{document_id}\"}}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/transactions/search")
async def semantic_search_transactions(
    query: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 4: FINANCIAL VECTOR SEARCH
    Uses pgvector to perform semantic similarity search across historical transactions.
    """
    workspace_id = uuid.UUID(current_user["workspace_id"])
    
    # Generate query embedding
    query_embedding = await llm_service.get_embedding(query)
    
    # Search closest transactions via <-> L2 distance
    stmt = (
        select(Transaction, FinancialDocument)
        .join(FinancialDocument, Transaction.financial_doc_id == FinancialDocument.id)
        .where(Transaction.workspace_id == workspace_id)
        .order_by(Transaction.embedding.l2_distance(query_embedding))
        .limit(10)
    )
    result = await db.execute(stmt)
    
    matches = []
    for txn, doc in result.all():
        matches.append({
            "vendor_name": doc.vendor_name,
            "description": txn.description,
            "amount": txn.amount,
            "currency": txn.currency,
            "is_anomaly": txn.is_anomaly,
            "anomaly_reason": txn.anomaly_reason
        })
    return matches

@router.get("/documents", response_model=List[FinancialDocumentResponse])
async def list_financial_documents(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = uuid.UUID(current_user["workspace_id"])
    result = await db.execute(select(FinancialDocument).where(FinancialDocument.workspace_id == workspace_id).order_by(FinancialDocument.created_at.desc()))
    return result.scalars().all()

@router.get("/findings", response_model=List[AuditFindingResponse])
async def list_audit_findings(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = uuid.UUID(current_user["workspace_id"])
    result = await db.execute(select(AuditFinding).where(AuditFinding.workspace_id == workspace_id).order_by(AuditFinding.created_at.desc()))
    return result.scalars().all()
