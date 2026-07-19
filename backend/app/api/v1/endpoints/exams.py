import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, Field, model_validator
from typing import Any, List, Optional, Dict
import uuid
import json
import tempfile
import os
from datetime import datetime, timezone

from app.db.session import get_db
from app.core.auth import get_current_user
from app.core.workspace import resolve_workspace_id
from app.models.document import Document, DocumentStatus
from app.models.exam import ExamPaper, ExamVersion
from app.schemas.exam import ExamPaperCreate, ExamPaperUpdate, ExamPaperResponse, GenerateQuestionRequest, ExamEditSaveRequest
from app.services.retrieval_service import RetrievalService
from app.services.llm_service import llm_service
from app.services.export_engine import ExportEngine
from app.services.table_extractor import get_table_extractor
from app.services.pdf_extractor import is_native_pdf

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── Task 6-T1: Section-Wise Paper Structure Models ──────────────────────────

class QuestionSubPart(BaseModel):
    """PART 2: per-question sub-part. Marks may be decimal."""
    label: str = Field(..., description='e.g. "a", "b", "c"')
    marks: float


class QuestionSpec(BaseModel):
    """PART 2: optional per-question spec. When a section provides a `questions`
    list, that list is authoritative (each question carries its own marks +
    optional sub_parts). When `questions` is empty/None, the generator falls
    back to the section-level (`count`, `marks_per_question`, `allow_subquestions`)
    shape so existing UIs keep working.
    """
    marks: float
    sub_parts: Optional[List[QuestionSubPart]] = None


class ExamSection(BaseModel):
    label: str           # "A", "B", "C"
    question_type: str   # "mcq", "short", "medium", "long", "case_study"
    total_marks: float   # decimal-friendly (e.g. 2.5 marks/question)
    count: int
    # deep-debug B4: SECTION-level toggle kept for backward compat. When
    # `questions` is provided per-question, that takes precedence (PART 2).
    allow_subquestions: bool = False
    # Optional per-question marks override. If unset, parent marks_per_question
    # = total_marks / count (so sub-questions get computed marks from there).
    marks_per_question: Optional[float] = None
    # PART 2 — per-question spec. If provided and non-empty, this is the
    # source of truth: each question controls its own marks + sub-parts.
    questions: Optional[List[QuestionSpec]] = None

    @model_validator(mode="after")
    def _coerce_question_marks(self) -> "ExamSection":
        # When per-question specs are provided, ensure `count` and
        # `total_marks` agree with them (callers may forget to recompute).
        if self.questions:
            self.count = len(self.questions)
            self.total_marks = round(
                sum(
                    (sum(sp.marks for sp in (q.sub_parts or [])) or q.marks)
                    for q in self.questions
                ),
                2,
            )
        return self


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
    # PART 1 — bind generation to the chat session so retrieval is scoped
    # to the documents the teacher uploaded for THIS paper. Optional for
    # backward compat with old clients, but required to get real grounded
    # questions (otherwise the backend can only output a refusal).
    chat_session_id: Optional[str] = None

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

def _fmt(n: float) -> str:
    return f"{n:.1f}".rstrip("0").rstrip(".") if n != int(n) else f"{int(n)}"


def _build_section_description(s: ExamSection) -> str:
    """Human-readable spec for the LLM. Honors per-question sub-parts (PART 2)."""
    if s.questions:
        per_q_lines = []
        for i, q in enumerate(s.questions, start=1):
            if q.sub_parts:
                sp_str = " + ".join(
                    f"({sp.label}) {_fmt(sp.marks)}" for sp in q.sub_parts
                )
                per_q_lines.append(
                    f"      Q{i}: {_fmt(sum(sp.marks for sp in q.sub_parts))} marks, "
                    f"split into sub-parts {sp_str}"
                )
            else:
                per_q_lines.append(f"      Q{i}: {_fmt(q.marks)} marks (single question, no sub-parts)")
        return (
            f"  Section {s.label} ({s.question_type.upper()}, total {_fmt(s.total_marks)} marks)\n"
            + "\n".join(per_q_lines)
        )
    marks_each = (
        s.marks_per_question
        if s.marks_per_question is not None
        else (s.total_marks / s.count if s.count else 0.0)
    )
    base = (
        f"  Section {s.label}: {s.count} {s.question_type.upper()} questions, "
        f"{_fmt(marks_each)} marks each (total {_fmt(s.total_marks)})"
    )
    if s.allow_subquestions:
        base += (
            ". Some questions in this section may be split into sub-parts (a),(b),(c) "
            "whose marks sum to the parent question's marks."
        )
    return base


async def _retrieve_grounding_for_paper(
    db: AsyncSession,
    *,
    request: ExamGenerationRequest,
    owner_id: uuid.UUID,
    chat_session_id: Optional[uuid.UUID],
) -> tuple[List[Dict[str, Any]], List[uuid.UUID], str]:
    """PART 1 — Pull chunks from the chat's attached docs that are relevant
    to the subject + section topics. Returns
        (evidence_chunks, doc_ids, doc_status_hint).

    `doc_status_hint` is one of:
      • ""             — found READY docs, retrieval proceeded.
      • "no_session"   — caller didn't provide a chat_session_id.
      • "no_docs"      — chat has zero attached docs (uploaded or otherwise).
      • "processing"   — chat HAS docs but none are READY yet.
      • "no_chunks"    — chat has READY docs but they didn't index any chunks.
    Caller uses the hint to pick the user-facing message.
    """
    if not chat_session_id:
        return [], [], "no_session"

    # 1. ALL docs in this chat (any status) — used to tell processing apart
    #    from missing.
    all_stmt = (
        select(Document.id, Document.status)
        .where(Document.chat_session_id == chat_session_id)
        .where(Document.owner_id == owner_id)
    )
    all_res = await db.execute(all_stmt)
    all_rows = all_res.all()
    if not all_rows:
        return [], [], "no_docs"

    ready_ids: List[uuid.UUID] = [
        row[0] for row in all_rows
        if (getattr(row[1], "value", row[1]) == DocumentStatus.READY.value)
    ]
    if not ready_ids:
        # We HAVE docs, just none are READY yet — different user-facing message.
        return [], [], "processing"
    doc_ids = ready_ids

    # 2. Run a retrieval query keyed by the subject — fetch a deeper pool
    #    than usual (3× the chunks the section descriptions imply) so we
    #    have wider topic coverage when the LLM writes ~10–20 questions.
    seed_query = f"{request.subject} {request.instructions or ''} key topics, definitions, formulas, examples".strip()
    target_k = min(40, max(20, sum(s.count for s in request.sections) * 2))
    payload = await RetrievalService.retrieve_chunks(
        db=db,
        query=seed_query,
        document_ids=doc_ids,
        top_k=target_k,
        similarity_threshold=0.0,
    )
    chunks = payload.get("results", []) or []
    # Sort by document + page so the LLM sees the syllabus in reading order.
    chunks = sorted(
        chunks,
        key=lambda c: (str(c.get("filename") or ""), int(c.get("page_number") or 0), int(c.get("chunk_index") or 0)),
    )
    if not chunks:
        return [], doc_ids, "no_chunks"
    return chunks, doc_ids, ""


@router.post("/generate/paper")
async def generate_paper(
    request: ExamGenerationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    6-T1 + 6-T2: Generate a section-wise exam paper with answer key.
    Validates marks before generation. Returns paper + answer_key + metadata.

    PART 1 — Real questions grounded in the chat's uploaded documents.
    The endpoint now:
      • requires chat_session_id (returns a clear 400 if no docs are attached),
      • retrieves chunks from those docs,
      • injects them into the LLM prompt as evidence with page citations,
      • on JSON parse failure, logs the raw LLM output and ONE retry; only
        then falls back to an explicit refusal (no more placeholder text).

    PART 3 — The generated paper is auto-saved to ExamPaper so Export DOCX
    always has something to export. The exam_id is returned in the payload.
    """
    # 6-T4: validate marks first.
    errors = validate_marks_allocation(request.sections, request.total_marks, request.bloom_distribution)
    if errors:
        raise HTTPException(status_code=400, detail={"validation_errors": errors})

    # PART 1: try to coerce chat_session_id (silently None on bad input).
    chat_uuid: Optional[uuid.UUID] = None
    if request.chat_session_id:
        try:
            chat_uuid = uuid.UUID(str(request.chat_session_id))
        except (ValueError, TypeError):
            chat_uuid = None

    owner_uuid = uuid.UUID(current_user["id"])
    workspace_uuid = resolve_workspace_id(current_user.get("workspace_id"))

    # PART 1: retrieve evidence chunks from the chat's attached docs.
    evidence, doc_ids, status_hint = await _retrieve_grounding_for_paper(
        db=db,
        request=request,
        owner_id=owner_uuid,
        chat_session_id=chat_uuid,
    )
    # B-fix — give the user a precise, actionable message based on which
    # condition actually failed. Returning the same generic "no documents
    # attached" for every empty case (as before) misled users who could see
    # a chip in the rail but were really hitting "still processing".
    if status_hint == "no_session":
        raise HTTPException(
            status_code=400,
            detail=(
                "Open a chat first, then attach a syllabus or textbook before "
                "generating a paper."
            ),
        )
    if status_hint == "no_docs":
        raise HTTPException(
            status_code=400,
            detail=(
                "No documents are attached to this chat. Upload a syllabus or "
                "textbook PDF/DOCX/PPTX before generating an exam paper so the "
                "questions can be grounded in real source material."
            ),
        )
    if status_hint == "processing":
        raise HTTPException(
            status_code=409,
            detail=(
                "The attached document is still being processed. Wait for the "
                "chip to turn green (Ready) and try again — usually takes "
                "10–60 seconds depending on document size."
            ),
        )
    if status_hint == "no_chunks":
        raise HTTPException(
            status_code=400,
            detail=(
                "The attached document(s) finished processing but no chunks "
                "matched the subject. Try a more specific subject name, or "
                "upload a syllabus that covers this topic."
            ),
        )

    # Compose the evidence block — page-cited and ordered.
    evidence_blocks = "\n\n".join(
        f"[{c.get('filename', 'doc')} | Page {c.get('page_number', '?')}]\n{c.get('text_content', '')}"
        for c in evidence
    )

    sections_desc = "\n".join(_build_section_description(s) for s in request.sections)
    bloom_desc = (
        ", ".join(f"{k}: {v}%" for k, v in request.bloom_distribution.items())
        if request.bloom_distribution else "Mixed levels"
    )

    # PART 1 + PART 3 layered system prompt. Strict grounding + JSON-only.
    system_prompt = (
        "You are an expert exam paper setter. Your job is to write REAL exam "
        "questions that are grounded ONLY in the evidence below. Do not invent "
        "facts. Each question must be answerable from the evidence. If a section "
        "asks for topics the evidence doesn't cover, write a question whose "
        "`text` clearly states 'The provided source material does not cover "
        "this topic.' rather than inventing.\n\n"
        f"EXAM CONTEXT:\n"
        f"- Subject: {request.subject}\n"
        f"- Board: {request.board}\n"
        f"- Total Marks: {_fmt(request.total_marks)}\n"
        f"- Duration: {request.duration_minutes} minutes\n"
        f"- Difficulty: {request.difficulty}\n"
        f"- Bloom's Taxonomy Distribution: {bloom_desc}\n"
        f"- Special Instructions: {request.instructions or 'None'}\n\n"
        f"SECTION SPECIFICATION (write EXACTLY this structure):\n{sections_desc}\n\n"
        f"EVIDENCE BLOCKS (your ONLY knowledge source):\n{evidence_blocks}\n\n"
        "OUTPUT — respond with ONLY valid JSON, no prose, no ``` fences."
    )

    schema_hint = (
        '{"paper":{"sections":[{"label":"A","question_type":"short","questions":'
        '[{"num":1,"text":"...","marks":2,"bloom_level":"Remember","difficulty":"easy",'
        '"options":["A","B","C","D"],"correct_index":0,'
        '"subparts":[{"label":"a","text":"...","marks":1},{"label":"b","text":"...","marks":1}]}]}]},'
        '"answer_key":[{"question_number":1,"correct_answer":"...","marking_scheme":"...","page_ref":"filename.pdf p.4",'
        '"bloom_level":"Remember","difficulty":"easy"}]}'
    )

    user_prompt = (
        f"Generate a complete {request.board} {request.subject} exam paper with "
        f"{len(request.sections)} sections totaling {_fmt(request.total_marks)} marks "
        f"({request.duration_minutes} minutes).\n"
        f"Return ONLY valid JSON exactly matching this schema:\n{schema_hint}\n\n"
        "Rules:\n"
        "- `subparts` is OPTIONAL; when present, sub-part marks MUST sum to the parent question's marks.\n"
        "- Marks may be fractional (e.g. 2.5).\n"
        "- For MCQ items, populate `options` (4 entries) and `correct_index` (0-3).\n"
        "- For short/medium/long/case_study items, set `options` to [] and `correct_index` to null.\n"
        "- Every question's `text` must reference real content from the evidence.\n"
        "- Every answer_key entry must include `page_ref` formatted as 'filename p.N'.\n"
    )

    # PART 1 — call the LLM, parse, log raw output on failure, ONE retry,
    # then refuse (don't ship placeholders).
    def _strip_fences(raw: str) -> str:
        s = (raw or "").strip()
        if s.startswith("```json"):
            s = s[7:]
        elif s.startswith("```"):
            s = s[3:]
        if s.endswith("```"):
            s = s[:-3]
        return s.strip()

    data: Optional[dict] = None
    last_raw: str = ""
    for attempt in range(2):
        try:
            raw = await llm_service.provider.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt
                + ("\n\nIMPORTANT: your previous output was not valid JSON. Output ONLY the JSON object."
                   if attempt > 0 else ""),
            )
            last_raw = raw or ""
            parsed = json.loads(_strip_fences(raw))
            if "paper" in parsed and "answer_key" in parsed:
                data = parsed
                break
            logger.warning(
                "[exams/generate/paper] attempt %d returned JSON missing required keys: %s",
                attempt + 1, list(parsed.keys()) if isinstance(parsed, dict) else type(parsed).__name__,
            )
        except json.JSONDecodeError as exc:
            logger.warning(
                "[exams/generate/paper] attempt %d JSON parse failed: %s; raw[:400]=%r",
                attempt + 1, exc, (last_raw or "")[:400],
            )
        except Exception as exc:
            logger.error("[exams/generate/paper] attempt %d LLM call failed: %s", attempt + 1, exc)
            break

    if not data:
        # PART 1: honest refusal — NEVER ship placeholder "[subject] question N on [subject]" anymore.
        data = _build_refusal_paper(request)

    data["metadata"] = {
        "total_marks": request.total_marks,
        "duration_minutes": request.duration_minutes,
        "board": request.board,
        "subject": request.subject,
        "difficulty": request.difficulty,
        "bloom_distribution": request.bloom_distribution,
        "doc_ids": [str(d) for d in doc_ids],
        "chunks_grounded": len(evidence),
    }
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    data["watermark"] = request.watermark

    # PART 3 — auto-save so Export DOCX can find it (and the user can revisit).
    try:
        new_exam = ExamPaper(
            workspace_id=workspace_uuid,
            owner_id=owner_uuid,
            title=f"{request.subject} — {request.board} {_fmt(request.total_marks)}-mark paper",
            description=f"Auto-saved {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
            content=data,  # Stored as JSON blob; loaded back for Export DOCX.
            status="DRAFT",
        )
        db.add(new_exam)
        await db.commit()
        await db.refresh(new_exam)
        data["exam_id"] = str(new_exam.id)
    except Exception as exc:
        # Don't fail the whole request if the save flops — surface the data,
        # and the user gets a soft warning that Export DOCX may not work until
        # the next attempt.
        logger.warning("[exams/generate/paper] auto-save failed: %s", exc)
        data["exam_id"] = None
        data["save_warning"] = "Auto-save failed — try regenerating before Export DOCX."

    return data


def _build_refusal_paper(request: ExamGenerationRequest) -> dict:
    """PART 1: Honest refusal — used ONLY when both LLM attempts fail to
    parse. Each section emits clearly-labelled refusal text instead of
    placeholder questions. The teacher can regenerate immediately.
    """
    sections = []
    answer_key = []
    q_num = 1
    refusal = (
        "[Generation failed] The model could not produce valid output for this "
        "section on the last attempt. Click Generate again, or simplify the "
        "section spec (e.g. fewer Bloom levels, narrower instructions)."
    )
    for s in request.sections:
        questions: List[dict] = []
        # Honour per-question shape when provided (PART 2).
        if s.questions:
            for i, q in enumerate(s.questions):
                q_marks = sum(sp.marks for sp in (q.sub_parts or [])) or q.marks
                rec = {
                    "num": q_num,
                    "text": refusal,
                    "marks": q_marks,
                    "bloom_level": "Understand",
                    "difficulty": request.difficulty,
                    "options": [],
                    "correct_index": None,
                }
                if q.sub_parts:
                    rec["subparts"] = [
                        {"label": sp.label, "text": refusal, "marks": sp.marks}
                        for sp in q.sub_parts
                    ]
                questions.append(rec)
                answer_key.append({
                    "question_number": q_num,
                    "correct_answer": "(no answer — generation failed)",
                    "marking_scheme": f"{_fmt(q_marks)} marks reserved.",
                    "bloom_level": "Understand",
                    "difficulty": request.difficulty,
                })
                q_num += 1
        else:
            marks_each = (
                s.marks_per_question
                if s.marks_per_question is not None
                else (s.total_marks / s.count if s.count else 0.0)
            )
            for i in range(s.count):
                rec = {
                    "num": q_num,
                    "text": refusal,
                    "marks": marks_each,
                    "bloom_level": "Understand",
                    "difficulty": request.difficulty,
                    "options": [],
                    "correct_index": None,
                }
                questions.append(rec)
                answer_key.append({
                    "question_number": q_num,
                    "correct_answer": "(no answer — generation failed)",
                    "marking_scheme": f"{_fmt(marks_each)} marks reserved.",
                    "bloom_level": "Understand",
                    "difficulty": request.difficulty,
                })
                q_num += 1
        sections.append({"label": s.label, "question_type": s.question_type, "questions": questions})
    return {"paper": {"sections": sections}, "answer_key": answer_key}


# ─── Task 6-T3: DOCX Export ──────────────────────────────────────────────────

@router.get("/{exam_id}/export/docx")
async def export_exam_docx(
    exam_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6-T3 / PART 3: Export a stored ExamPaper as an academically formatted DOCX.

    Accepts either:
      • a real UUID (the new auto-save path returns one in `exam_id`), or
      • the literal string `"latest"` — pull the most recent DRAFT for this
        workspace + owner, for clients that didn't capture the id.
    """
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    owner_id = uuid.UUID(current_user["id"])

    if exam_id == "latest":
        stmt = (
            select(ExamPaper)
            .where(ExamPaper.workspace_id == workspace_id)
            .where(ExamPaper.owner_id == owner_id)
            .order_by(ExamPaper.created_at.desc())
            .limit(1)
        )
    else:
        try:
            exam_uuid = uuid.UUID(exam_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid exam_id format.")
        stmt = (
            select(ExamPaper)
            .where(ExamPaper.id == exam_uuid)
            .where(ExamPaper.workspace_id == workspace_id)
            .where(ExamPaper.owner_id == owner_id)
        )

    result = await db.execute(stmt)
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(
            status_code=404,
            detail=(
                "Couldn't find the exam to export. Generate the paper first; "
                "the auto-save step persists it before this endpoint can run."
            ),
        )

    exam_data = {
        "title": exam.title,
        "content": exam.content,
        "status": exam.status,
        "watermark": "FINAL" if exam.status == "FINAL" else "DRAFT",
    }

    docx_bytes = ExportEngine.generate_exam_docx(exam_data)
    safe_title = (exam.title or "exam_paper").replace(" ", "_")[:40]
    filename = f"exam_{safe_title}_{exam.id}.docx"

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

    # L-3: storage_path may be an S3 key, not a disk path — download via
    # storage_service to a temp file (same pattern as document_tasks) so
    # table extraction works for both local and S3 deployments.
    import asyncio
    from app.core.storage import storage_service

    _ext = os.path.splitext(doc.filename or "")[1].lower() or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=_ext) as tmp_file:
        local_path = tmp_file.name
    try:
        try:
            await asyncio.to_thread(
                storage_service.download_file, doc.storage_path, local_path
            )
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Document file not found in storage")

        # Determine if scanned: native PDF = selectable text present
        is_scanned = not is_native_pdf(local_path)

        extractor = get_table_extractor()
        tables = await extractor.extract_tables(local_path, is_scanned=is_scanned)
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)

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

# PART 6 Phase 1 — dedicated edit-save endpoint. The editor stores a
# free-form `content` blob (with `edited_html` alongside the original
# `paper`/`answer_key`); the strict ExamPaperUpdate.content schema can't
# accept that shape. This endpoint accepts the blob verbatim.
@router.post("/{exam_id}/save-edits", response_model=ExamPaperResponse)
async def save_exam_edits(
    exam_id: str,
    payload: ExamEditSaveRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        exam_uuid = uuid.UUID(exam_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam_id format.")

    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    owner_id = uuid.UUID(current_user["id"])
    stmt = (
        select(ExamPaper)
        .where(ExamPaper.id == exam_uuid)
        .where(ExamPaper.workspace_id == workspace_id)
        .where(ExamPaper.owner_id == owner_id)
    )
    result = await db.execute(stmt)
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found.")

    exam.content = payload.content
    try:
        await db.commit()
        await db.refresh(exam)
    except Exception as exc:
        await db.rollback()
        logger.error(f"[exams/save-edits] failed for {exam_id}: {exc}")
        raise HTTPException(status_code=500, detail="Could not save edits.")
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
