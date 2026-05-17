from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Any
import uuid
import asyncio

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.legal import Contract, Clause, ComplianceRule, RedlineSuggestion, ApprovalWorkflow
from app.models.document import Document
from app.schemas.legal import (
    ContractResponse, ComplianceRuleCreate, ComplianceRuleResponse, 
    ContractSegmentationSchema, ClauseComplianceSchema
)
from app.services.llm_service import llm_service
from app.workers.tasks.legal_tasks import process_contract_batch

router = APIRouter()

@router.post("/rules", response_model=ComplianceRuleResponse)
async def create_compliance_rule(
    request: ComplianceRuleCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = uuid.UUID(current_user["workspace_id"])
    rule = ComplianceRule(
        workspace_id=workspace_id,
        name=request.name,
        category=request.category,
        rule_description=request.rule_description,
        mandatory=request.mandatory
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule

@router.get("/rules", response_model=List[ComplianceRuleResponse])
async def list_rules(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = uuid.UUID(current_user["workspace_id"])
    result = await db.execute(select(ComplianceRule).where(ComplianceRule.workspace_id == workspace_id))
    return result.scalars().all()

@router.post("/contracts/process")
async def process_contract(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 1: ASYNC LEGAL PROCESSING
    Offloads heavy compliance processing to Celery workers.
    """
    workspace_id = uuid.UUID(current_user["workspace_id"])
    doc = (await db.execute(select(Document).where(Document.id == document_id, Document.workspace_id == workspace_id))).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Dispatch to Celery
    process_contract_batch.delay(str(document_id), str(workspace_id))
    
    return {"status": "processing_queued", "document_id": str(document_id)}

@router.get("/events/legal/{document_id}")
async def sse_legal_processing_updates(
    document_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    """
    PHASE 1: Live Processing Updates
    Server-Sent Events (SSE) endpoint to push contract processing status.
    """
    async def event_generator():
        # Simulated heartbeat for SSE UI update
        for i in range(1, 10):
            await asyncio.sleep(2)
            yield f"data: {{\"status\": \"processing\", \"progress\": {i * 10}, \"document_id\": \"{document_id}\"}}\n\n"
        yield f"data: {{\"status\": \"complete\", \"document_id\": \"{document_id}\"}}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/clauses/search")
async def semantic_search_clauses(
    query: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 2: LEGAL VECTOR SEARCH
    Uses pgvector to perform semantic similarity search across historical clauses.
    """
    workspace_id = uuid.UUID(current_user["workspace_id"])
    
    # Generate query embedding
    query_embedding = await llm_service.get_embedding(query)
    
    # Search closest clauses via <-> L2 distance
    stmt = (
        select(Clause, Contract)
        .join(Contract, Clause.contract_id == Contract.id)
        .where(Clause.workspace_id == workspace_id)
        .order_by(Clause.embedding.l2_distance(query_embedding))
        .limit(10)
    )
    result = await db.execute(stmt)
    
    matches = []
    for clause, contract in result.all():
        matches.append({
            "contract_title": contract.title,
            "section_name": clause.section_name,
            "original_text": clause.original_text,
            "clause_type": clause.clause_type,
            "risk_level": clause.risk_level
        })
    return matches

@router.post("/contracts/{contract_id}/approvals")
async def add_contract_approval(
    contract_id: uuid.UUID,
    status: str,
    comments: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 4: LEGAL COLLABORATION
    Adds an approval or rejection decision to the contract's audit timeline.
    """
    workspace_id = uuid.UUID(current_user["workspace_id"])
    reviewer_id = uuid.UUID(current_user["id"])
    
    approval = ApprovalWorkflow(
        workspace_id=workspace_id,
        contract_id=contract_id,
        reviewer_id=reviewer_id,
        status=status,
        comments=comments
    )
    db.add(approval)
    
    contract = (await db.execute(select(Contract).where(Contract.id == contract_id))).scalar_one_or_none()
    if contract:
        contract.status = status
        
    await db.commit()
    return {"status": "success"}

@router.get("/contracts", response_model=List[ContractResponse])
async def list_contracts(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = uuid.UUID(current_user["workspace_id"])
    result = await db.execute(select(Contract).where(Contract.workspace_id == workspace_id).order_by(Contract.created_at.desc()))
    return result.scalars().all()

@router.get("/contracts/{contract_id}/clauses")
async def get_contract_clauses(
    contract_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = uuid.UUID(current_user["workspace_id"])
    
    stmt = (
        select(Clause, RedlineSuggestion)
        .outerjoin(RedlineSuggestion, Clause.id == RedlineSuggestion.clause_id)
        .where(Clause.contract_id == contract_id, Clause.workspace_id == workspace_id)
        .order_by(Clause.created_at.asc())
    )
    result = await db.execute(stmt)
    
    clauses_dict = {}
    for clause, redline in result.all():
        if clause.id not in clauses_dict:
            clauses_dict[clause.id] = {
                "clause": clause,
                "redlines": []
            }
        if redline:
            clauses_dict[clause.id]["redlines"].append(redline)
            
    return list(clauses_dict.values())
