import uuid
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import logging

from app.db.session import get_db, AsyncSessionLocal
from app.core.auth import get_current_user
from app.models.export_job import ExportJob
from app.models.legal import Contract, Clause
from app.schemas.export import ExportJobCreate, ExportJobResponse
from app.workers.tasks.export_tasks import process_export_job
from app.services.export_engine import export_engine

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/legal/{contract_id}/docx")
async def export_legal_contract(contract_id: str, current_user: dict = Depends(get_current_user)):
    """
    PHASE 4: REAL EXPORT ENGINE
    Generates a DOCX format redline review for Legal Workspaces.
    """
    async with AsyncSessionLocal() as db:
        # Fetch contract with clauses and redlines
        stmt = select(Contract).where(Contract.id == contract_id).options(
            selectinload(Contract.clauses).selectinload(Clause.redlines)
        )
        contract = (await db.execute(stmt)).scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
            
        # Format data for engine
        clauses_data = []
        for clause in contract.clauses:
            c_data = {
                "clause": {
                    "section_name": clause.section_name,
                    "original_text": clause.original_text,
                    "risk_level": clause.risk_level,
                    "compliance_notes": clause.compliance_notes
                },
                "redlines": [{"suggested_text": r.suggested_text} for r in clause.redlines]
            }
            clauses_data.append(c_data)

    # Generate DOCX in memory
    try:
        file_stream = export_engine.generate_legal_redline_docx(contract.title, clauses_data)
        
        # PHASE 9: SECURITY HARDENING
        # Ensure headers prevent caching of sensitive files
        headers = {
            'Content-Disposition': f'attachment; filename="redline_{contract.id}.docx"',
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        }
        return StreamingResponse(file_stream, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers=headers)
        
    except Exception as e:
        logger.error(f"DOCX Export Failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate DOCX file.")

@router.post("", response_model=ExportJobResponse)
async def create_export_job(
    request: ExportJobCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger an asynchronous background export job.
    Enforces strict tenant isolation.
    """
    job = ExportJob(
        owner_id=uuid.UUID(current_user["id"]),
        workspace_id=uuid.UUID(current_user["workspace_id"]),
        format=request.format,
        export_type=request.export_type,
        payload=request.payload
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Trigger Celery Task
    contract_id = request.payload.get("contract_id", "") if request.payload else ""
    process_export_job.delay(contract_id, str(job.id))
    
    return job

@router.get("", response_model=List[ExportJobResponse])
async def list_exports(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Fetch all export jobs for the current tenant's workspace."""
    stmt = select(ExportJob).where(
        ExportJob.workspace_id == uuid.UUID(current_user["workspace_id"])
    ).order_by(ExportJob.created_at.desc())
    
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{job_id}", response_model=ExportJobResponse)
async def get_export_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Poll export job status."""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid Job ID format.")

    stmt = select(ExportJob).where(
        ExportJob.id == job_uuid,
        ExportJob.workspace_id == uuid.UUID(current_user["workspace_id"])
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found or access denied.")
        
    return job
