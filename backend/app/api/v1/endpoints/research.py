from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Any, Optional
import uuid
import asyncio
import json
import logging

from pydantic import BaseModel

from app.db.session import get_db
from app.core.auth import get_current_user
from app.core.workspace import resolve_workspace_id
from app.models.research import ResearchProject, ResearchPaper, ResearchFinding, ContradictionReport
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.schemas.research import PaperExtractionSchema, ContradictionVerdictSchema
from app.services.llm_service import llm_service
from app.workers.tasks.research_tasks import process_research_batch

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Task 6-R1 / 6-X1: Citation schemas ───────────────────────────────────────

CITATION_FORMATS = {"APA", "MLA", "IEEE", "Chicago", "BibTeX", "Vancouver"}

class CitationRequest(BaseModel):
    doc_ids: List[str]
    format: str  # APA | MLA | IEEE | Chicago | BibTeX | Vancouver

class GapsRequest(BaseModel):
    doc_ids: List[str]

class DeepResearchRequest(BaseModel):
    query: str
    doc_ids: List[str] = []
    session_id: Optional[str] = None

# ── Citation formatters (Python string formatting — never LLM) ────────────────

def _initials(full_name: str) -> str:
    """Convert 'First Last' → 'F. L.'"""
    parts = full_name.strip().split()
    return " ".join(p[0].upper() + "." for p in parts if p)

def _format_apa(m: dict, idx: int) -> str:
    author = m.get("author", "Unknown Author")
    year   = m.get("year", "n.d.")
    title  = m.get("title", "Untitled")
    journal = m.get("journal", "")
    volume  = m.get("volume", "")
    issue   = m.get("issue", "")
    pages   = m.get("pages", "")
    doi     = m.get("doi", "")
    vol_issue = f"{volume}({issue})" if volume and issue else volume or ""
    citation = f"{author} ({year}). {title}. {journal}"
    if vol_issue:
        citation += f", {vol_issue}"
    if pages:
        citation += f", {pages}"
    citation += "."
    if doi:
        citation += f" https://doi.org/{doi}"
    return citation

def _format_mla(m: dict, idx: int) -> str:
    author  = m.get("author", "Unknown Author")
    title   = m.get("title", "Untitled")
    journal = m.get("journal", "")
    volume  = m.get("volume", "")
    issue   = m.get("issue", "")
    year    = m.get("year", "n.d.")
    pages   = m.get("pages", "")
    parts = [f'{author}. "{title}." {journal}']
    if volume:
        parts[-1] += f" vol.{volume}"
    if issue:
        parts[-1] += f", no.{issue}"
    parts[-1] += f", {year}"
    if pages:
        parts[-1] += f", pp. {pages}"
    return parts[-1] + "."

def _format_ieee(m: dict, idx: int) -> str:
    author  = m.get("author", "Unknown")
    title   = m.get("title", "Untitled")
    journal = m.get("journal", "")
    volume  = m.get("volume", "")
    issue   = m.get("issue", "")
    pages   = m.get("pages", "")
    year    = m.get("year", "n.d.")
    citation = f'[{idx}] {author}, "{title}," {journal}'
    if volume:
        citation += f", vol. {volume}"
    if issue:
        citation += f", no. {issue}"
    if pages:
        citation += f", pp. {pages}"
    citation += f", {year}."
    return citation

def _format_chicago(m: dict, idx: int) -> str:
    author  = m.get("author", "Unknown Author")
    title   = m.get("title", "Untitled")
    journal = m.get("journal", "")
    volume  = m.get("volume", "")
    issue   = m.get("issue", "")
    year    = m.get("year", "n.d.")
    pages   = m.get("pages", "")
    citation = f'{author}. "{title}." {journal} {volume}'
    if issue:
        citation += f", no. {issue}"
    citation += f" ({year})"
    if pages:
        citation += f": {pages}"
    return citation + "."

def _format_bibtex(m: dict, idx: int) -> str:
    last_name = m.get("author", "Unknown").split(",")[0].strip()
    year = m.get("year", "XXXX")
    key  = f"{last_name}{year}{idx}"
    return (
        f"@article{{{key},\n"
        f"  author  = {{{m.get('author', '')}}},\n"
        f"  title   = {{{m.get('title', '')}}},\n"
        f"  journal = {{{m.get('journal', '')}}},\n"
        f"  year    = {{{year}}},\n"
        f"  volume  = {{{m.get('volume', '')}}},\n"
        f"  number  = {{{m.get('issue', '')}}},\n"
        f"  pages   = {{{m.get('pages', '')}}},\n"
        f"  doi     = {{{m.get('doi', '')}}}\n"
        f"}}"
    )

def _format_vancouver(m: dict, idx: int) -> str:
    author  = m.get("author", "Unknown")
    title   = m.get("title", "Untitled")
    journal = m.get("journal", "")
    year    = m.get("year", "n.d.")
    volume  = m.get("volume", "")
    issue   = m.get("issue", "")
    pages   = m.get("pages", "")
    citation = f"{idx}. {author}. {title}. {journal}."
    if year:
        citation += f" {year}"
    if volume:
        citation += f";{volume}"
    if issue:
        citation += f"({issue})"
    if pages:
        citation += f":{pages}"
    return citation + "."

FORMAT_DISPATCH = {
    "APA":       _format_apa,
    "MLA":       _format_mla,
    "IEEE":      _format_ieee,
    "Chicago":   _format_chicago,
    "BibTeX":    _format_bibtex,
    "Vancouver": _format_vancouver,
}

# ── Task 6-R1 / 6-X1: Citation endpoint ──────────────────────────────────────

@router.post("/citations")
async def export_citations(
    body: CitationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fmt = body.format.strip()
    if fmt not in CITATION_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{fmt}'. Choose from: {', '.join(sorted(CITATION_FORMATS))}",
        )

    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    citations: List[str] = []

    for raw_id in body.doc_ids:
        try:
            doc_id = uuid.UUID(raw_id)
        except ValueError:
            continue

        doc = (await db.execute(
            select(Document).where(Document.id == doc_id, Document.workspace_id == workspace_id)
        )).scalar_one_or_none()
        if not doc:
            continue

        # Pull a sample of text chunks for context
        chunk_result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc_id)
            .limit(6)
        )
        chunks = chunk_result.scalars().all()
        context = "\n\n".join(c.text_content for c in chunks if c.text_content)[:3000]

        system_prompt = (
            "You are a bibliographic metadata extractor. "
            "Given document text, extract the citation metadata as a single JSON object. "
            "Return ONLY valid JSON, no extra text. "
            'Keys: author (string, "Last, First" format), title (string), '
            "journal (string), year (4-digit string), doi (string), "
            "volume (string), issue (string), pages (string), publisher (string). "
            "Use empty string for any field not found."
        )
        user_prompt = (
            f"Document filename: {doc.filename}\n\n"
            f"Document content (excerpt):\n{context}"
        )

        try:
            raw = await llm_service.generate(system_prompt, user_prompt)
            # Strip markdown fences if present
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            metadata = json.loads(raw.strip())
        except Exception as exc:
            logger.warning("Citation extraction failed for %s: %s", doc.filename, exc)
            metadata = {"author": "", "title": doc.filename, "journal": "", "year": "",
                        "doi": "", "volume": "", "issue": "", "pages": "", "publisher": ""}

        idx = len(citations) + 1
        formatter = FORMAT_DISPATCH[fmt]
        citations.append(formatter(metadata, idx))

    return {"citations": citations, "format": fmt, "count": len(citations)}

# ── Task 6-R2: Research gaps endpoint ────────────────────────────────────────

@router.post("/gaps")
async def find_research_gaps(
    body: GapsRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = resolve_workspace_id(current_user["workspace_id"])

    all_context_parts: List[str] = []
    for raw_id in body.doc_ids:
        try:
            doc_id = uuid.UUID(raw_id)
        except ValueError:
            continue

        doc = (await db.execute(
            select(Document).where(Document.id == doc_id, Document.workspace_id == workspace_id)
        )).scalar_one_or_none()
        if not doc:
            continue

        chunk_result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc_id)
            .limit(8)
        )
        chunks = chunk_result.scalars().all()
        text = "\n\n".join(c.text_content for c in chunks if c.text_content)[:2000]
        if text:
            all_context_parts.append(f"[{doc.filename}]\n{text}")

    if not all_context_parts:
        raise HTTPException(status_code=400, detail="No readable document content found.")

    combined = "\n\n---\n\n".join(all_context_parts)[:8000]

    system_prompt = (
        "You are a systematic literature review assistant. "
        "Analyze the provided research paper excerpts and identify: "
        "(1) research gaps — unexplored areas and open questions, "
        "(2) conflicts — areas where papers contradict each other, "
        "(3) consensus — areas of strong agreement across papers. "
        "Return ONLY a valid JSON object with keys 'gaps', 'conflicts', 'consensus'. "
        "Each value is an array of concise descriptive strings (3-8 items each). "
        "No extra commentary, no markdown fences — pure JSON only."
    )
    user_prompt = f"Research papers:\n\n{combined}"

    try:
        raw = await llm_service.generate(system_prompt, user_prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        gaps      = result.get("gaps", [])
        conflicts = result.get("conflicts", [])
        consensus = result.get("consensus", [])
    except Exception as exc:
        logger.warning("Gap analysis failed: %s", exc)
        gaps      = ["Gap analysis could not be completed — please try again."]
        conflicts = []
        consensus = []

    return {"gaps": gaps, "conflicts": conflicts, "consensus": consensus}

@router.post("/projects")
async def create_project(
    title: str,
    description: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    project = ResearchProject(workspace_id=workspace_id, title=title, description=description)
    db.add(project)
    await db.commit()
    return {"status": "success", "project_id": project.id}

@router.post("/process")
async def process_research_document(
    document_id: uuid.UUID,
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 1: ASYNC RESEARCH PIPELINE
    Offloads heavy paper validation and extraction to Celery workers.
    """
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    doc = (await db.execute(select(Document).where(Document.id == document_id, Document.workspace_id == workspace_id))).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Dispatch to Celery
    process_research_batch.delay(str(document_id), str(workspace_id), str(project_id))
    
    return {"status": "processing_queued", "document_id": str(document_id)}

@router.get("/events/research/{document_id}")
async def sse_research_processing_updates(
    document_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    """
    PHASE 1: Live Processing Updates
    Server-Sent Events (SSE) endpoint to push research pipeline status.
    """
    # M-1: real Document.status transitions instead of a fake heartbeat.
    from app.services.processing_events import document_status_event_stream
    return StreamingResponse(
        document_status_event_stream(document_id, current_user["id"]),
        media_type="text/event-stream",
    )

@router.get("/search")
async def semantic_search_research(
    query: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 3: RESEARCH VECTOR SEARCH
    Uses pgvector to perform semantic similarity search across Findings.
    """
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    query_embedding = await llm_service.get_embedding(query)
    
    stmt = (
        select(ResearchFinding, ResearchPaper)
        .join(ResearchPaper, ResearchFinding.paper_id == ResearchPaper.id)
        .where(ResearchFinding.workspace_id == workspace_id)
        .order_by(ResearchFinding.embedding.l2_distance(query_embedding))
        .limit(10)
    )
    result = await db.execute(stmt)
    
    matches = []
    for finding, paper in result.all():
        matches.append({
            "statement": finding.statement,
            "evidence": finding.evidence_quote,
            "paper_title": paper.title,
            "authors": paper.authors
        })
    return matches

@router.get("/copilot/chat")
async def ai_copilot_chat(
    query: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 4: AI RESEARCH COPILOT
    SSE endpoint for streaming research chat responses grounded in retrieved papers.
    """
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    
    try:
        query_embedding = await llm_service.get_embedding(query)
        stmt = select(ResearchFinding).where(
            ResearchFinding.workspace_id == workspace_id
        ).order_by(ResearchFinding.embedding.l2_distance(query_embedding)).limit(3)
        findings = (await db.execute(stmt)).scalars().all()
    except Exception as exc:
        logger.warning("[Research Copilot] Vector search failed, falling back to recency: %s", exc)
        stmt = select(ResearchFinding).where(
            ResearchFinding.workspace_id == workspace_id
        ).order_by(ResearchFinding.created_at.desc()).limit(3)
        findings = (await db.execute(stmt)).scalars().all()
    context = "\n".join([f"Finding: {f.statement}\nEvidence: {f.evidence_quote}" for f in findings])

    # M-8: findings content is untrusted document text; direct
    # provider.generate_stream bypasses LLMService.generate, so harden here.
    from app.services.llm_service import _harden_system_prompt
    system_prompt = _harden_system_prompt(
        "You are an expert research copilot. Use the provided research findings as your primary "
        "source of truth. Synthesise evidence clearly, cite findings where relevant, and never "
        "invent citations. If the findings don't cover the topic, say so honestly and offer "
        "what general scientific knowledge you can."
    )
    user_prompt = (
        f"Relevant research findings:\n{context}\n\n"
        f"Researcher question: {query}\n\n"
        "Please provide a concise, evidence-based response."
    )

    async def chat_stream_generator():
        try:
            async for token in llm_service.provider.generate_stream(system_prompt, user_prompt):
                if token:
                    yield f"data: {token}\n\n"
        except Exception as e:
            logger.error(f"[Research Copilot] LLM stream error: {e}")
            yield f"data: [ERROR] Unable to generate response.\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(chat_stream_generator(), media_type="text/event-stream")

@router.post("/deep-research")
async def deep_research(
    body: DeepResearchRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """N-1: expose the 4-step Deep Research agent.

    The agent (RAG → gap analysis → Tavily web search → synthesis, with a
    Veritas trust score) existed but had no caller anywhere. Streams one
    SSE `data:` frame per ResearchEvent, ending with [DONE]. Document ids
    are validated against the caller's ownership before the agent runs.
    """
    from app.services.deep_research_agent import deep_research_agent

    owner_id = uuid.UUID(current_user["id"])
    valid_doc_ids: List[str] = []
    for raw_id in body.doc_ids:
        try:
            doc_id = uuid.UUID(raw_id)
        except ValueError:
            continue
        doc = (await db.execute(
            select(Document).where(Document.id == doc_id, Document.owner_id == owner_id)
        )).scalar_one_or_none()
        if doc:
            valid_doc_ids.append(str(doc_id))

    async def event_generator():
        try:
            async for event in deep_research_agent.research(
                body.query, valid_doc_ids, session_id=body.session_id, db=db
            ):
                yield f"data: {json.dumps(event.to_dict())}\n\n"
        except Exception:
            logger.error("[DeepResearch] stream failed", exc_info=True)
            yield f"data: {json.dumps({'step': 'final', 'status': 'error', 'message': 'Deep research failed. Please retry.'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/synthesis/{project_id}")
async def synthesize_project(
    project_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 2: CROSS-DOCUMENT SYNTHESIS

    H-4: real analysis (this endpoint previously returned hardcoded fake
    clusters/contradictions). Extract-then-compute split: Python owns the
    clustering (cosine over stored finding embeddings), consensus scores,
    and severity; the LLM only classifies the relationship of candidate
    cross-paper pairs. Response keys unchanged (frontend contract).
    """
    import numpy as np

    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    rows = (await db.execute(
        select(ResearchFinding, ResearchPaper.title)
        .join(ResearchPaper, ResearchFinding.paper_id == ResearchPaper.id)
        .where(
            ResearchPaper.project_id == project_id,
            ResearchFinding.workspace_id == workspace_id,
        )
    )).all()

    if not rows:
        return {"status": "success", "clusters": [], "contradictions": []}

    embedded = [
        (f, title, np.asarray(f.embedding, dtype=float))
        for f, title in rows if f.embedding is not None
    ]
    unembedded = [(f, title) for f, title in rows if f.embedding is None]

    def _cos(a: "np.ndarray", b: "np.ndarray") -> float:
        denom = float(np.linalg.norm(a) * np.linalg.norm(b)) or 1e-9
        return float(np.dot(a, b) / denom)

    # 1. Greedy centroid-free clustering: a finding joins the first cluster
    #    whose seed it matches at >= 0.75 cosine (deterministic, no LLM).
    grouped: list = []
    for item in embedded:
        for cluster in grouped:
            if _cos(item[2], cluster[0][2]) >= 0.75:
                cluster.append(item)
                break
        else:
            grouped.append([item])

    clusters_payload = []
    for cluster in grouped:
        pair_sims = [
            _cos(a[2], b[2])
            for i, a in enumerate(cluster) for b in cluster[i + 1:]
        ]
        consensus = round(sum(pair_sims) / len(pair_sims), 2) if pair_sims else 1.0
        representative = max(cluster, key=lambda it: len(it[0].statement))
        clusters_payload.append({
            "topic": representative[0].statement,
            "consensus_score": consensus,
            "findings": [
                {"statement": it[0].statement, "paper": it[1]} for it in cluster
            ],
        })
    for f, title in unembedded:
        clusters_payload.append({
            "topic": f.statement,
            "consensus_score": 1.0,
            "findings": [{"statement": f.statement, "paper": title}],
        })

    # 2. Contradiction candidates: cross-paper pairs on a similar topic
    #    (cosine 0.60–0.97; near-duplicates excluded), top 5 by similarity.
    candidate_pairs = []
    for i, a in enumerate(embedded):
        for b in embedded[i + 1:]:
            if a[0].paper_id == b[0].paper_id:
                continue
            sim = _cos(a[2], b[2])
            if 0.60 <= sim < 0.97:
                candidate_pairs.append((sim, a, b))
    candidate_pairs.sort(key=lambda p: -p[0])

    contradictions_payload = []
    for sim, a, b in candidate_pairs[:5]:
        try:
            verdict = await llm_service.generate_json(
                query=(
                    "Do these two research findings agree, contradict each "
                    "other, or address unrelated points? Classify the relationship."
                ),
                grounded_context=(
                    f"Finding A ({a[1]}): {a[0].statement}\n"
                    f"Finding B ({b[1]}): {b[0].statement}"
                ),
                response_schema=ContradictionVerdictSchema,
            )
        except Exception as exc:
            # No fabricated verdicts: skip the pair, loudly.
            logger.error(f"[Synthesis] Contradiction check failed for pair "
                         f"({a[0].id}, {b[0].id}): {exc}")
            continue
        if verdict.verdict == "contradict":
            contradictions_payload.append({
                "description": verdict.description,
                "severity": "HIGH" if sim >= 0.80 else "MEDIUM",
            })
            db.add(ContradictionReport(
                workspace_id=workspace_id,
                finding_a_id=a[0].id,
                finding_b_id=b[0].id,
                description=verdict.description,
            ))
    if contradictions_payload:
        await db.commit()

    return {
        "status": "success",
        "clusters": clusters_payload,
        "contradictions": contradictions_payload,
    }

@router.get("/projects")
async def list_projects(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    result = await db.execute(select(ResearchProject).where(ResearchProject.workspace_id == workspace_id).limit(limit).offset(offset))
    return [{"id": p.id, "title": p.title, "description": p.description} for p in result.scalars().all()]

@router.get("/projects/{project_id}/papers")
async def list_papers(
    project_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    result = await db.execute(select(ResearchPaper).where(ResearchPaper.project_id == project_id, ResearchPaper.workspace_id == workspace_id))
    return [{"id": p.id, "title": p.title, "abstract": p.abstract} for p in result.scalars().all()]

@router.get("/papers/{paper_id}/findings")
async def list_findings(
    paper_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    result = await db.execute(select(ResearchFinding).where(ResearchFinding.paper_id == paper_id, ResearchFinding.workspace_id == workspace_id))
    return [{"id": f.id, "statement": f.statement, "evidence": f.evidence_quote, "methodology": f.methodology} for f in result.scalars().all()]
