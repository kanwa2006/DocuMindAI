from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import uuid

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.exam import ExamPaper, ExamVersion
from app.schemas.exam import ExamPaperCreate, ExamPaperUpdate, ExamPaperResponse, GenerateQuestionRequest
from app.services.retrieval_service import RetrievalService
from app.services.llm_service import llm_service

router = APIRouter()

@router.post("", response_model=ExamPaperResponse)
async def create_exam(
    request: ExamPaperCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = uuid.UUID(current_user["workspace_id"])
    owner_id = uuid.UUID(current_user["id"])
    
    db_exam = ExamPaper(
        workspace_id=workspace_id,
        owner_id=owner_id,
        title=request.title,
        description=request.description,
        content=request.content.model_dump()
    )
    db.add(db_exam)
    await db.commit()
    await db.refresh(db_exam)
    return db_exam

@router.get("", response_model=List[ExamPaperResponse])
async def list_exams(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = uuid.UUID(current_user["workspace_id"])
    stmt = select(ExamPaper).where(ExamPaper.workspace_id == workspace_id).order_by(ExamPaper.updated_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{exam_id}", response_model=ExamPaperResponse)
async def get_exam(
    exam_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = uuid.UUID(current_user["workspace_id"])
    stmt = select(ExamPaper).where(ExamPaper.id == exam_id, ExamPaper.workspace_id == workspace_id)
    result = await db.execute(stmt)
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam

@router.put("/{exam_id}", response_model=ExamPaperResponse)
async def update_exam(
    exam_id: uuid.UUID,
    request: ExamPaperUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = uuid.UUID(current_user["workspace_id"])
    stmt = select(ExamPaper).where(ExamPaper.id == exam_id, ExamPaper.workspace_id == workspace_id)
    result = await db.execute(stmt)
    exam = result.scalar_one_or_none()
    
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if request.save_version:
        version = ExamVersion(exam_id=exam.id, content=exam.content, version_tag=request.version_tag)
        db.add(version)

    if request.title:
        exam.title = request.title
    if request.description is not None:
        exam.description = request.description
    if request.content is not None:
        exam.content = request.content.model_dump()
    if request.status:
        exam.status = request.status
        
    await db.commit()
    await db.refresh(exam)
    return exam

@router.post("/generate/question")
async def generate_exam_question(
    request: GenerateQuestionRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 1 & 2: Grounded Question and Answer Key Generation
    Uses Hybrid RRF Retrieval to fetch context, then LLM generates strict schemas.
    """
    workspace_id = uuid.UUID(current_user["workspace_id"])
    
    # 1. Retrieve hybrid semantic context
    retrieval_result = await RetrievalService.retrieve_chunks(
        db=db,
        query=request.topic,
        workspace_id=workspace_id,
        document_ids=request.document_ids,
        top_k=5
    )
    
    evidence_blocks = [f"[{chunk['filename']}, Page {chunk['page_number']}] {chunk['text_content']}" for chunk in retrieval_result.get("results", [])]
    grounded_context = "\n\n".join(evidence_blocks)
    
    # 2. Call LLM Service with Strict JSON Generation + Validation Repair Loop
    try:
        from app.schemas.exam import QuestionSchema
        question_query = f"Create a question about {request.topic} with {request.marks} marks. Difficulty: {request.difficulty}."
        validated_question = await llm_service.generate_json(
            query=question_query,
            grounded_context=grounded_context,
            response_schema=QuestionSchema
        )
        generated_question = validated_question.model_dump()
        generated_question["id"] = str(uuid.uuid4()) # Fresh ID for frontend
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"LLM failed to generate valid structured question: {str(e)}")
        
    return {"status": "success", "question": generated_question, "retrieval_diagnostics": retrieval_result["tracing"]}

@router.post("/generate/diagram")
async def generate_diagram(
    topic: str,
    current_user: dict = Depends(get_current_user)
):
    """
    PHASE 5: Diagram Generation (Mermaid/Graphviz)
    Generates structured SVG-compatible flowchart descriptions.
    """
    return {
        "type": "mermaid",
        "content": f"graph TD;\n    A[{topic} Introduction] --> B[Core Components];\n    B --> C[Implementation];\n    C --> D[Evaluation];"
    }

@router.post("/process/voice")
async def process_voice_notes(
    current_user: dict = Depends(get_current_user)
):
    """
    PHASE 4: Voice -> Exam Pipeline Stub
    In production, this uploads a file, triggers Whisper.cpp Celery task, 
    and returns a structured exam block.
    """
    return {"status": "processing", "message": "Voice processing queued via Celery."}
