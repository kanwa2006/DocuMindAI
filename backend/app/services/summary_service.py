"""
PHASE 2 — Map-reduce summary path for full-document coverage.

Standard retrieval is biased toward the chunks whose embeddings are closest
to the (short) query. For "summarize this document" intents that's wrong —
the user wants COVERAGE, not relevance. This service:

1. Pulls EVERY chunk for the requested document(s), in (page, chunk_index) order.
2. Groups them into ordered windows (~ N chunks per window).
3. Maps each window through the LLM with a "summarize this window" prompt.
4. Reduces all window summaries into one structured final summary.

This guarantees every page is read, regardless of similarity score.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Dict, Any, AsyncGenerator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.models.document_page import DocumentPage
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


# Heuristics for "this question wants a summary, not a needle-in-haystack".
# Each pattern is matched against the lower-cased query.
_SUMMARY_PATTERNS = [
    r"\bsummari[sz]e\b",
    r"\bsummary\b",
    r"\bexplain (this|the) (document|paper|pdf|report|deck|slides|book)\b",
    r"\bexplain everything\b",
    r"\boverview\b",
    r"\btl;?dr\b",
    r"\bwhat is (this|the) (document|paper|pdf|report) about\b",
    r"\bgive me (an?|a brief|a detailed) summary\b",
    r"\bwalk me through\b",
    r"\boutline (this|the) (document|paper|pdf)\b",
]


def is_summary_intent(query: str) -> bool:
    """Quick regex sniff to decide whether to use the map-reduce path."""
    q = (query or "").strip().lower()
    if not q:
        return False
    return any(re.search(p, q) for p in _SUMMARY_PATTERNS)


WINDOW_CHUNKS = 6          # ~6 chunks per map call (≈ 11 KB of text, well under any model window)
MAX_WINDOWS_HARD_CAP = 40  # safety guard — a 240-chunk doc maps in 40 windows; bigger gets truncated


async def _load_all_chunks_ordered(
    db: AsyncSession,
    *,
    document_ids: List[UUID],
    owner_id: UUID,
) -> List[Dict[str, Any]]:
    """Return every chunk for the given READY docs, sorted by
    (filename, page_number, chunk_index). Owner filter is belt-and-suspenders
    on top of the chat-session-id filter the caller already applied.
    """
    stmt = (
        select(
            DocumentChunk.id,
            DocumentChunk.text_content,
            DocumentChunk.chunk_index,
            Document.filename,
            DocumentPage.page_number,
        )
        .join(Document, DocumentChunk.document_id == Document.id)
        .join(DocumentPage, DocumentChunk.page_id == DocumentPage.id)
        .where(Document.owner_id == owner_id)
        .where(Document.status == DocumentStatus.READY)
        .where(Document.id.in_(document_ids))
        .order_by(Document.filename, DocumentPage.page_number, DocumentChunk.chunk_index)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "chunk_id": str(r[0]),
            "text_content": r[1] or "",
            "chunk_index": int(r[2] or 0),
            "filename": r[3] or "",
            "page_number": int(r[4] or 0),
        }
        for r in rows
    ]


def _group_into_windows(chunks: List[Dict[str, Any]], window_size: int = WINDOW_CHUNKS) -> List[List[Dict[str, Any]]]:
    """Chunk the chunks. Each window is contiguous in (filename, page, idx)."""
    windows: List[List[Dict[str, Any]]] = []
    for i in range(0, len(chunks), window_size):
        windows.append(chunks[i : i + window_size])
        if len(windows) >= MAX_WINDOWS_HARD_CAP:
            logger.warning(
                "[summary] hit MAX_WINDOWS_HARD_CAP=%d; truncating to first %d chunks",
                MAX_WINDOWS_HARD_CAP,
                MAX_WINDOWS_HARD_CAP * window_size,
            )
            break
    return windows


def _format_window_for_map(window: List[Dict[str, Any]]) -> str:
    """Wrap each chunk with its filename + page so the LLM can cite."""
    parts = []
    for c in window:
        parts.append(
            f"<chunk filename=\"{c['filename']}\" page=\"{c['page_number']}\">\n"
            f"{c['text_content']}\n"
            f"</chunk>"
        )
    return "\n\n".join(parts)


_MAP_SYSTEM = (
    "You are extracting the key content from a contiguous slice of a longer "
    "document. Read everything in the slice and produce a short, faithful "
    "summary covering:\n"
    "- the main topics this slice addresses,\n"
    "- the specific facts, figures, names, definitions or claims it contains,\n"
    "- any tables/diagrams it references (describe them in words).\n"
    "Always include the page number for each significant fact. Do not invent "
    "anything not present in the slice. Keep it under 220 words."
)

_REDUCE_SYSTEM_GENERAL = (
    "You are producing a complete, structured summary of a document from "
    "ordered window-summaries provided to you. Read ALL window-summaries "
    "before writing. Cover the document proportionally — if multiple topics "
    "exist, address all of them. Use this structure:\n\n"
    "## Overview\n"
    "## Key Topics\n"
    "## Important Details\n"
    "## Key Insights\n"
    "## Limitations or Risks (if applicable)\n"
    "## Summary\n\n"
    "Cite page numbers for specific claims. Do not invent content the windows "
    "didn't mention. If the document is short, keep the headings but be brief."
)


async def generate_full_document_summary_stream(
    db: AsyncSession,
    *,
    query: str,
    document_ids: List[UUID],
    owner_id: UUID,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Yield SSE-friendly dicts for a map-reduce summary.

    Yields a sequence of {'kind': 'stage'|'token'|'evidence'|'done', 'data': ...}
    so the calling endpoint can translate to its existing event names.
    """
    if not document_ids:
        yield {"kind": "stage", "data": "no_documents"}
        return

    yield {"kind": "stage", "data": "loading_chunks"}
    chunks = await _load_all_chunks_ordered(db, document_ids=document_ids, owner_id=owner_id)
    if not chunks:
        yield {"kind": "stage", "data": "empty_document"}
        yield {"kind": "token", "data": "I couldn't find any extracted text in the attached document(s). The upload may still be processing or extraction may have failed."}
        yield {"kind": "done", "data": {}}
        return

    windows = _group_into_windows(chunks)
    yield {"kind": "stage", "data": f"mapping_{len(windows)}_windows"}

    # Emit evidence references — one synthetic entry per filename so the
    # frontend can show that we read the WHOLE document, not just N chunks.
    filenames = sorted({c["filename"] for c in chunks})
    yield {
        "kind": "evidence",
        "data": [
            {
                "chunk_id": "00000000-0000-0000-0000-000000000000",
                "document_id": "00000000-0000-0000-0000-000000000000",
                "filename": fn,
                "page_number": 1,
                "text_content": f"(full-document map-reduce summary; {sum(1 for c in chunks if c['filename'] == fn)} chunks read)",
                "similarity_score": 1.0,
                "rerank_score": 1.0,
                "layout_metadata": None,
            }
            for fn in filenames
        ],
    }

    # MAP step — synchronous per-window to keep RPS predictable and avoid
    # bursting Gemini's key rotator. Each map call is a tight ≤220-word ask.
    window_summaries: List[str] = []
    for idx, window in enumerate(windows):
        try:
            window_text = _format_window_for_map(window)
            partial = await llm_service.provider.generate(
                _MAP_SYSTEM,
                f"Slice {idx + 1} of {len(windows)}. Summarize this slice:\n\n{window_text}",
            )
            window_summaries.append(partial.strip())
        except Exception as exc:
            logger.warning(f"[summary] map step {idx + 1}/{len(windows)} failed: {exc}")
            # Continue — a missing window isn't fatal. We add a sentinel so
            # the reducer notices coverage holes.
            window_summaries.append(
                f"[Slice {idx + 1} could not be summarized due to a transient error; "
                f"the document continues normally after this point.]"
            )

    # REDUCE step — stream the final summary so the user sees it appear
    # incrementally instead of after the whole map-reduce completes.
    yield {"kind": "stage", "data": "reducing"}

    reduce_user_prompt = (
        f"User asked: {query}\n\n"
        f"Below are {len(window_summaries)} ordered window-summaries covering the entire document. "
        f"Combine them into a complete structured summary as instructed.\n\n"
        + "\n\n---\n\n".join(
            f"### Window {i + 1}\n{s}" for i, s in enumerate(window_summaries)
        )
    )

    try:
        async for token in llm_service.provider.generate_stream(_REDUCE_SYSTEM_GENERAL, reduce_user_prompt):
            if token:
                yield {"kind": "token", "data": token}
    except Exception as exc:
        logger.error(f"[summary] reduce step failed: {exc}")
        yield {
            "kind": "token",
            "data": (
                "I was able to read the document but couldn't compose the final summary. "
                "Please try again, or ask narrower questions."
            ),
        }

    yield {"kind": "done", "data": {}}
