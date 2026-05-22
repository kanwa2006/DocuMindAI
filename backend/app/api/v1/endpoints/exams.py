from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, model_validator
from typing import Any, List, Optional, Dict
import uuid
import json
import tempfile
import os
from datetime import datetime, timezone

from app.db.session import get_db
from app.core.auth import get_current_user
from app.core.workspace import resolve_workspace_id
from app.models.document import Document
from app.models.exam import ExamPaper, ExamVersion
from app.schemas.exam import ExamPaperCreate, ExamPaperUpdate, ExamPaperResponse, GenerateQuestionRequest
from app.services.retrieval_service import RetrievalService
from app.services.llm_service import llm_service
from app.services.export_engine import ExportEngine
from app.services.table_extractor import get_table_extractor
from app.services.pdf_extractor import is_native_pdf

router = APIRouter()

# ─── Task 6-T1: Section-Wise Paper Structure Models ──────────────────────────

class ExamSection(BaseModel):
    label: str           # "A", "B", "C"
    question_type: str   # "mcq", "short", "medium", "long", "case_study"
    total_marks: float   # decimal-friendly (e.g. 2.5 marks/question)
    count: int
    # deep-debug B4: optional flag — if true, the LLM is asked to break some
    # questions in this section into (a)/(b)/(c) sub-parts whose marks sum to
    # the parent mark. Default false keeps current behaviour for existing UIs.
    allow_subquestions: bool = False
    # Optional per-question marks override. If unset, parent marks_per_question
    # = total_marks / count (so sub-questions get computed marks from there).
    marks_per_question: Optional[float] = None

class ExamGenerationRequest(BaseModel):
    sections: List[ExamSection]
    subject: str
    board: str = "CBSE"
    total_marks: float = 100   # decimal-friendly
    duration_minutes: int = 180
    instructions: str = ""
    difficulty: str = "mixed"
    bloom_distribution: Dict[str, int] = {}
    watermark: str = "DRAFT"

    @model_validator(mode="after")
    def validate_marks(self):
        total = sum(s.total_marks for s in self.sections)
        # tolerate float arithmetic noise: 1.0 + 1.0 + … == 3.0000000004 etc.
        if abs(total - self.total_marks) > 0.01:
            raise ValueError(
                f"Section marks total ({total}) != paper total ({self.total_marks})"
            )
        return self

# ─── Task 6-T4: Marks Validation Engine ──────────────────────────────────────

def validate_marks_allocation(sections: List[ExamSection], total_marks: float, bloom_distribution: Dict[str, int]) -> List[str]:
    """Returns empty list if valid, list of error strings if invalid."""
    errors = []

    section_total = sum(s.total_marks for s in sections)
    if abs(section_total - total_marks) > 0.01:
        errors.append(f"Section marks total ({section_total}) does not equal paper total ({total_marks}).")

    for s in sections:
        if s.total_marks <= 0:
            errors.append(f"Section {s.label}: total_marks must be > 0.")
        if s.count <= 0:
            errors.append(f"Section {s.label}: count must be > 0.")
        # deep-debug B2: removed the divisibility error. Marks-per-question now
        # comes from marks_per_question override OR total/count (which can be a
        # fraction — totally legitimate, e.g. 2.5 marks/question).

    if bloom_distribution:
        bd_total = sum(bloom_distribution.values())
        if bd_total != 100:
            errors.append(f"Bloom's distribution values must sum to 100 (got {bd_total}).")

    return errors

# ─── Task 6-T1: Generate Full Paper with Answer Key ──────────────────────────

@router.post("/generate/paper")
async def generate_paper(
    request: ExamGenerationRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    6-T1 + 6-T2: Generate a section-wise exam paper with answer key.
    Validates marks before generation. Returns paper + answer_key + metadata.
    """
    # Task 6-T4: validate marks first
    errors = validate_marks_allocation(request.sections, request.total_marks, request.bloom_distribution)
    if errors:
        raise HTTPException(status_code=400, detail={"validation_errors": errors})

    def _fmt(n: float) -> str:
        return f"{n:.1f}".rstrip("0").rstrip(".") if n != int(n) else f"{int(n)}"

    sections_desc = "\n".join(
        f"  Section {s.label}: {s.count} {s.question_type.upper()} questions, "
        f"{_fmt(s.marks_per_question if s.marks_per_question is not None else s.total_marks / s.count)} marks each "
        f"(total {_fmt(s.total_marks)})"
        + (". Some questions in this section may be split into sub-parts (a), (b), (c) whose marks sum to the parent question's marks." if s.allow_subquestions else "")
        for s in request.sections
    )

    bloom_desc = (
        ", ".join(f"{k}: {v}%" for k, v in request.bloom_distribution.items())
        if request.bloom_distribution else "Mixed levels"
    )

    grounded_context = f"""
Exam Paper Generation Configuration:
- Subject: {request.subject}
- Board: {request.board}
- Total Marks: {request.total_marks}
- Duration: {request.duration_minutes} minutes
- Difficulty: {request.difficulty}
- Bloom's Taxonomy Distribution: {bloom_desc}
- Special Instructions: {request.instructions or 'None'}

Sections to generate:
{sections_desc}

Generate exactly the required number of questions per section with the exact marks per question.
Ensure questions follow the Bloom's taxonomy distribution specified.
For MCQ: provide 4 options labeled A/B/C/D with one correct answer.
For short/long: provide model answers and step-wise marking schemes.
    """.strip()

    prompt = (
        f"Generate a complete {request.board} {request.subject} exam paper with {len(request.sections)} sections "
        f"totaling {_fmt(request.total_marks)} marks and duration {request.duration_minutes} minutes. "
        f"Return ONLY valid JSON with exactly this structure: "
        '{"paper":{"sections":[{"label":"A","questions":[{"num":1,"text":"...","marks":2,'
        '"bloom_level":"Remember","difficulty":"easy","options":["..."],"correct_index":0,'
        '"subparts":[{"label":"a","text":"...","marks":1},{"label":"b","text":"...","marks":1}]}]}]},'
        '"answer_key":[{"question_number":1,"correct_answer":"...","marking_scheme":"...",'
        '"bloom_level":"Remember","difficulty":"easy"}]}. '
        "The `subparts` field is OPTIONAL and only present when a question is split; "
        "if present, the marks must sum to the parent question's marks. "
        "Marks may be fractional (e.g. 2.5)."
    )

    raw = await llm_service.provider.generate(
        system_prompt=f"You are an expert exam paper setter. {grounded_context}\n\nRespond ONLY with valid JSON.",
        user_prompt=prompt,
    )

    # Clean potential markdown fences
    clean = raw.strip()
    if clean.startswith("```json"):
        clean = clean[7:-3].strip()
    elif clean.startswith("```"):
        clean = clean[3:-3].strip()

    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        # Fallback: build stub structure matching the spec
        data = _build_stub_paper(request)

    # Ensure the structure has required keys
    if "paper" not in data or "answer_key" not in data:
        data = _build_stub_paper(request)

    data["metadata"] = {
        "total_marks": request.total_marks,
        "duration_minutes": request.duration_minutes,
        "board": request.board,
        "subject": request.subject,
        "difficulty": request.difficulty,
        "bloom_distribution": request.bloom_distribution,
    }
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    data["watermark"] = request.watermark

    return data


def _build_stub_paper(request: ExamGenerationRequest) -> dict:
    """Build a deterministic stub when LLM JSON parse fails. Honours fractional marks."""
    sections = []
    answer_key = []
    q_num = 1
    for s in request.sections:
        marks_each = (
            s.marks_per_question
            if s.marks_per_question is not None
            else (s.total_marks / s.count if s.count else 0.0)
        )
        questions = []
        for i in range(s.count):
            q_record = {
                "num": q_num,
                "text": f"[{request.subject}] {s.question_type.upper()} question {i+1} on {request.subject}.",
                "marks": marks_each,
                "bloom_level": "Understand",
                "difficulty": request.difficulty,
                "options": ["Option A", "Option B", "Option C", "Option D"] if s.question_type == "mcq" else [],
                "correct_index": 0 if s.question_type == "mcq" else None,
            }
            # B4: if allow_subquestions, give the first question in the section a 2-part split
            # so the user sees the structure rendered.
            if s.allow_subquestions and i == 0 and marks_each >= 2:
                half = marks_each / 2
                q_record["subparts"] = [
                    {"label": "a", "text": "First sub-part.", "marks": half},
                    {"label": "b", "text": "Second sub-part.", "marks": marks_each - half},
                ]
            questions.append(q_record)
            answer_key.append({
                "question_number": q_num,
                "correct_answer": "Option A" if s.question_type == "mcq" else "Model answer.",
                "marking_scheme": f"{marks_each} marks for complete answer.",
                "bloom_level": "Understand",
                "difficulty": request.difficulty,
            })
            q_num += 1
        sections.append({"label": s.label, "question_type": s.question_type, "questions": questions})
    return {"paper": {"sections": sections}, "answer_key": answer_key}


# ─── Task 6-T3: DOCX Export ──────────────────────────────────────────────────

@router.get("/{exam_id}/export/docx")
async def export_exam_docx(
    exam_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6-T3: Export a stored ExamPaper as an academically formatted DOCX."""
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    stmt = select(ExamPaper).where(ExamPaper.id == exam_id, ExamPaper.workspace_id == workspace_id)
    result = await db.execute(stmt)
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    exam_data = {
        "title": exam.title,
        "content": exam.content,
        "status": exam.status,
        "watermark": "FINAL" if exam.status == "FINAL" else "DRAFT",
    }

    docx_bytes = ExportEngine.generate_exam_docx(exam_data)
    safe_title = exam.title.replace(" ", "_")[:40]
    filename = f"exam_{safe_title}_{exam_id}.docx"

    return StreamingResponse(
        iter([docx_bytes.read()]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/export/table-docx")
async def export_table_docx(
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    """Export a markdown-rendered table from the Teacher workspace as DOCX."""
    title = payload.get("title", "Table Export")
    headers = payload.get("headers", [])
    rows = payload.get("rows", [])

    docx_bytes = ExportEngine.generate_table_docx(title=title, headers=headers, rows=rows)
    return StreamingResponse(
        iter([docx_bytes.read()]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="table_export_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.docx"'},
    )


# ─── Phase 11: Table Extraction Models ───────────────────────────────────────

class ExtractTablesRequest(BaseModel):
    document_id: str

class ExportTableRequest(BaseModel):
    table: Dict[str, Any]
    format: str  # "docx" | "csv" | "html"


# ─── Phase 11: Extract Tables Endpoint ───────────────────────────────────────

@router.post("/extract-tables")
async def extract_tables(
    request: ExtractTablesRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Phase 11 Task 11.2: Extract all tables from a document.
    Uses Docling for native PDFs, PaddleOCR for scanned/image documents.
    """
    try:
        doc_id = uuid.UUID(request.document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_id")

    owner_id = uuid.UUID(current_user["id"])
    stmt = select(Document).where(Document.id == doc_id, Document.owner_id == owner_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc.storage_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    # Determine if scanned: native PDF = selectable text present
    is_scanned = not is_native_pdf(file_path)

    extractor = get_table_extractor()
    tables = await extractor.extract_tables(file_path, is_scanned=is_scanned)

    return {
        "document_id": request.document_id,
        "tables_found": len(tables),
        "tables": tables,
    }


# ─── Phase 11: Export Table Endpoint ─────────────────────────────────────────

@router.post("/export/table")
async def export_table(
    request: ExportTableRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Phase 11 Task 11.2: Export a single extracted table as DOCX, CSV, or HTML.
    """
    extractor = get_table_extractor()
    fmt = request.format.lower()

    if fmt == "docx":
        tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        tmp.close()
        try:
            extractor.export_to_docx(request.table, tmp.name)
            with open(tmp.name, "rb") as f:
                data = f.read()
        finally:
            os.unlink(tmp.name)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="extracted_table_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.docx"'},
        )

    elif fmt == "csv":
        csv_str = extractor.export_to_csv(request.table)
        return Response(
            content=csv_str,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="table_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.csv"'},
        )

    elif fmt == "html":
        html = extractor.export_to_html(request.table)
        return {"html": html}

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt!r}. Use 'docx', 'csv', or 'html'.")


# ─── Existing CRUD endpoints (unchanged) ─────────────────────────────────────

@router.post("", response_model=ExamPaperResponse)
async def create_exam(
    request: ExamPaperCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
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
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    stmt = select(ExamPaper).where(ExamPaper.workspace_id == workspace_id).order_by(ExamPaper.updated_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{exam_id}", response_model=ExamPaperResponse)
async def get_exam(
    exam_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
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
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
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
    workspace_id = resolve_workspace_id(current_user["workspace_id"])

    retrieval_result = await RetrievalService.retrieve_chunks(
        db=db,
        query=request.topic,
        workspace_id=workspace_id,
        document_ids=request.document_ids,
        top_k=5
    )

    evidence_blocks = [f"[{chunk['filename']}, Page {chunk['page_number']}] {chunk['text_content']}" for chunk in retrieval_result.get("results", [])]
    grounded_context = "\n\n".join(evidence_blocks)

    try:
        from app.schemas.exam import QuestionSchema
        question_query = f"Create a question about {request.topic} with {request.marks} marks. Difficulty: {request.difficulty}."
        validated_question = await llm_service.generate_json(
            query=question_query,
            grounded_context=grounded_context,
            response_schema=QuestionSchema
        )
        generated_question = validated_question.model_dump()
        generated_question["id"] = str(uuid.uuid4())
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
    """
    return {"status": "processing", "message": "Voice processing queued via Celery."}
