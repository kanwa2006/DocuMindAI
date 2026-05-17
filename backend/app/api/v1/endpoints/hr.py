from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, func, String
from typing import List, Any, Optional
import uuid
import csv
import io
import asyncio

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.hr import JobRole, CandidateProfile, JobMatch, CandidateNote
from app.models.document import Document
from app.schemas.hr import (
    JobRoleCreate, JobRoleResponse, CandidateProfileResponse, JobMatchResponse, 
    CandidateExtractionSchema, MatchAnalysisSchema, CandidateNoteCreate, CandidateNoteResponse
)
from app.services.llm_service import llm_service
from app.workers.tasks.hr_tasks import process_resume_batch

router = APIRouter()

@router.post("/jobs", response_model=JobRoleResponse)
async def create_job_role(
    request: JobRoleCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = uuid.UUID(current_user["workspace_id"])
    owner_id = uuid.UUID(current_user["id"])
    
    job = JobRole(
        workspace_id=workspace_id,
        owner_id=owner_id,
        title=request.title,
        department=request.department,
        description=request.description,
        requirements=request.requirements
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job

@router.get("/jobs", response_model=List[JobRoleResponse])
async def list_jobs(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = uuid.UUID(current_user["workspace_id"])
    stmt = select(JobRole).where(JobRole.workspace_id == workspace_id).order_by(JobRole.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/jobs/{job_id}/candidates/process")
async def process_candidate(
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 1: True Async Bulk Processing
    Triggers background Celery task to prevent API blocking.
    """
    workspace_id = uuid.UUID(current_user["workspace_id"])
    
    job_stmt = select(JobRole).where(JobRole.id == job_id, JobRole.workspace_id == workspace_id)
    if not (await db.execute(job_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job not found")
        
    doc_stmt = select(Document).where(Document.id == document_id, Document.workspace_id == workspace_id)
    if not (await db.execute(doc_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")

    # Dispatch to Celery Main Queue
    process_resume_batch.delay(str(job_id), str(document_id), str(workspace_id))
    
    return {"status": "queued", "message": "Resume processing started in background."}

@router.get("/jobs/{job_id}/candidates", response_model=List[Any])
async def list_job_candidates(
    job_id: uuid.UUID,
    search: Optional[str] = Query(None, description="Semantic keyword search"),
    min_score: Optional[float] = Query(0.0),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 2: Advanced Candidate Search
    Returns filtered and semantically sorted candidates.
    """
    workspace_id = uuid.UUID(current_user["workspace_id"])
    
    stmt = (
        select(JobMatch, CandidateProfile)
        .join(CandidateProfile, JobMatch.candidate_id == CandidateProfile.id)
        .where(JobMatch.job_id == job_id, JobMatch.workspace_id == workspace_id)
        .where(JobMatch.fit_score >= min_score)
    )
    
    if status:
        stmt = stmt.where(JobMatch.status == status)
        
    if search:
        # PHASE 2: Semantic Candidate Search
        # In a full pgvector implementation, we would convert `search` to an embedding
        # and sort by `<->` (L2 distance) or `<#>` (inner product).
        # We simulate the hybrid structure here:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                CandidateProfile.name.ilike(search_pattern),
                CandidateProfile.skills.cast(String).ilike(search_pattern)
            )
        )
        # To order by pgvector semantic distance:
        # embedding = await llm_service.get_embedding(search)
        # stmt = stmt.order_by(CandidateProfile.embedding.l2_distance(embedding))
    else:
        stmt = stmt.order_by(JobMatch.fit_score.desc())
        
    result = await db.execute(stmt)
    records = result.all()
    
    # Return formatted response
    return [
        {
            "match": match,
            "profile": profile
        }
        for match, profile in records
    ]

@router.get("/jobs/{job_id}/analytics")
async def get_job_analytics(
    job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 4: HR Analytics Dashboard
    Returns applicant funnel and distribution data.
    """
    workspace_id = uuid.UUID(current_user["workspace_id"])
    
    stmt = select(JobMatch.status, func.count(JobMatch.id)).where(
        JobMatch.job_id == job_id, JobMatch.workspace_id == workspace_id
    ).group_by(JobMatch.status)
    result = await db.execute(stmt)
    status_counts = dict(result.all())
    
    return {
        "funnel": {
            "total_candidates": sum(status_counts.values()),
            "new": status_counts.get("NEW", 0),
            "shortlisted": status_counts.get("SHORTLISTED", 0),
            "interviewing": status_counts.get("INTERVIEW", 0),
            "rejected": status_counts.get("REJECTED", 0)
        }
    }

@router.get("/jobs/{job_id}/candidates/export/csv")
async def export_candidates_csv(
    job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 2: HR Export System (CSV)
    Streams a CSV file of candidates for a specific job.
    """
    workspace_id = uuid.UUID(current_user["workspace_id"])
    
    stmt = (
        select(JobMatch, CandidateProfile)
        .join(CandidateProfile, JobMatch.candidate_id == CandidateProfile.id)
        .where(JobMatch.job_id == job_id, JobMatch.workspace_id == workspace_id)
        .order_by(JobMatch.fit_score.desc())
    )
    result = await db.execute(stmt)
    records = result.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Candidate Name", "Email", "Phone", "Years Exp", "Top Skills", "ATS Fit Score", "Status", "Missing Skills"])
    
    for match, profile in records:
        analysis = match.match_analysis or {}
        missing = ", ".join(analysis.get("missing_skills", []))
        skills = ", ".join(profile.skills[:5])
        writer.writerow([
            profile.name, profile.email, profile.phone, profile.experience_years, 
            skills, round(match.fit_score or 0), match.status, missing
        ])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]), 
        media_type="text/csv", 
        headers={"Content-Disposition": f"attachment; filename=candidates_job_{job_id}.csv"}
    )

@router.get("/events/processing/{job_id}")
async def sse_processing_updates(
    job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    """
    PHASE 1: Live Processing Updates
    Server-Sent Events (SSE) endpoint to push processing status to the frontend.
    """
    async def event_generator():
        # In production, this would subscribe to a Redis Pub/Sub channel
        # For this demonstration, we push heartbeat messages simulating progress
        for i in range(1, 10):
            await asyncio.sleep(2)
            yield f"data: {{\"status\": \"processing\", \"progress\": {i * 10}, \"job_id\": \"{job_id}\"}}\n\n"
        yield f"data: {{\"status\": \"complete\", \"job_id\": \"{job_id}\"}}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/candidates/{candidate_id}/notes", response_model=CandidateNoteResponse)
async def add_candidate_note(
    candidate_id: uuid.UUID,
    request: CandidateNoteCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 1: Recruiter Collaboration
    Add a threaded note/comment to a candidate.
    """
    workspace_id = uuid.UUID(current_user["workspace_id"])
    author_id = uuid.UUID(current_user["id"])
    
    note = CandidateNote(
        workspace_id=workspace_id,
        candidate_id=candidate_id,
        author_id=author_id,
        content=request.content
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note

@router.get("/candidates/{candidate_id}/notes", response_model=List[CandidateNoteResponse])
async def get_candidate_notes(
    candidate_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves chronological activity timeline / recruiter notes for a candidate."""
    workspace_id = uuid.UUID(current_user["workspace_id"])
    stmt = select(CandidateNote).where(
        CandidateNote.candidate_id == candidate_id,
        CandidateNote.workspace_id == workspace_id
    ).order_by(CandidateNote.created_at.desc())
    
    result = await db.execute(stmt)
    return result.scalars().all()

@router.put("/matches/{match_id}/status")
async def update_match_status(
    match_id: uuid.UUID,
    status: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = uuid.UUID(current_user["workspace_id"])
    stmt = select(JobMatch).where(JobMatch.id == match_id, JobMatch.workspace_id == workspace_id)
    match = (await db.execute(stmt)).scalar_one_or_none()
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
        
    match.status = status
    await db.commit()
    return {"status": "success", "new_status": status}
