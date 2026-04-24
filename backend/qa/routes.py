import json
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from backend.db.database import get_db
from backend.db.models import User, ChatHistory, ChatSession, Document
from backend.auth.routes import get_current_user
from backend.qa.indexer import query_user_index
from backend.qa.chain import answer_question, classify_query
from backend.qa.evaluation import evaluate_qa_pair
from backend.config import TOP_K_RESULTS

router = APIRouter(prefix="/qa", tags=["qa"])


class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[int] = None
    uploaded_doc_ids: Optional[List[int]] = None


class SessionRenameRequest(BaseModel):
    title: str


def _clean_filename(filename):
    basename = os.path.basename(filename)
    parts = basename.split("_", 1)
    if len(parts) == 2 and len(parts[0]) == 32 and parts[0].isalnum():
        return parts[1]
    return basename


def _get_session_history(db, session_id, user_id, limit=6):
    return list(reversed(
        db.query(ChatHistory)
        .filter(ChatHistory.session_id == session_id, ChatHistory.user_id == user_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit).all()
    ))


def _is_followup(question, history):
    if not history:
        return False
    q = question.lower().strip()
    return (
        q.startswith(("it ", "that ", "this ", "they ", "and ", "but ", "so ", "why ", "when ",
                      "where ", "what about ", "how about ", "can u ", "can you ")) or
        any(w in q for w in ["more about", "explain more", "elaborate", "give example",
                             "simplify", "tell me more", "expand", "previous", "above",
                             "related to", "continue", "briefly", "in detail", "summarize it",
                             "explain it", "what is it", "describe it"])
    )


def _build_conv_context(history):
    if not history:
        return ""
    parts = ["=== PREVIOUS CONVERSATION ==="]
    for c in history[-4:]:
        parts.append(f"Student: {c.question}")
        preview = c.answer[:400] + "..." if len(c.answer) > 400 else c.answer
        parts.append(f"AI: {preview}")
        parts.append("---")
    parts.append("=== END ===\n")
    return "\n".join(parts)


def _auto_title(question):
    q = question.strip()
    return q[:50] + ("..." if len(q) > 50 else "")


def _get_session_doc_names(db, user_id: int, doc_ids: List[int]) -> List[str]:
    if not doc_ids:
        return []
    docs = db.query(Document).filter(
        Document.id.in_(doc_ids),
        Document.user_id == user_id,
        Document.is_indexed == 1
    ).all()
    return [_clean_filename(d.filename) for d in docs]


def _get_all_user_ready_docs(db, user_id: int) -> List[str]:
    docs = db.query(Document).filter(
        Document.user_id == user_id,
        Document.is_indexed == 1
    ).all()
    return [_clean_filename(d.filename) for d in docs]


@router.post("/sessions")
def create_session(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = ChatSession(user_id=current_user.id, title="New Chat")
    db.add(session)
    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "message_count": 0,
        "preview": "Empty chat"
    }


@router.get("/sessions")
def list_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.updated_at.desc()).all()

    result = []
    for s in sessions:
        count = db.query(ChatHistory).filter(ChatHistory.session_id == s.id).count()
        first = db.query(ChatHistory).filter(
            ChatHistory.session_id == s.id
        ).order_by(ChatHistory.created_at).first()

        result.append({
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
            "message_count": count,
            "preview": (first.question[:60] + "..." if first and len(first.question) > 60
                        else (first.question if first else "Empty chat")),
            "doc_ids": json.loads(s.doc_ids or "[]"),
        })
    return result


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id, ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(404, "Session not found")
    db.query(ChatHistory).filter(ChatHistory.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"message": "Session deleted"}


@router.patch("/sessions/{session_id}")
def rename_session(session_id: int, req: SessionRenameRequest,
                   current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id, ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(404, "Session not found")
    session.title = req.title[:100]
    db.commit()
    return {"id": session.id, "title": session.title}


@router.post("/ask")
def ask_question(req: QuestionRequest,
                 current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    if not req.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    session_id = req.session_id
    if not session_id:
        session = ChatSession(user_id=current_user.id, title=_auto_title(req.question))
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id
    else:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id, ChatSession.user_id == current_user.id
        ).first()
        if not session:
            raise HTTPException(404, "Session not found")
        if session.title == "New Chat":
            session.title = _auto_title(req.question)
        session.updated_at = datetime.utcnow()
        db.commit()

    history = _get_session_history(db, session_id, current_user.id)
    is_followup = _is_followup(req.question, history)
    conv_context = _build_conv_context(history) if is_followup else ""

    question = req.question.strip()
    q_lower = question.lower()
    query_type = classify_query(question)
    vague = [
        "explain it", "explain it briefly", "explain briefly", "what is this",
        "what is it", "describe it", "tell me about it", "what is this about",
        "explain this", "what does it say", "brief summary", "brief explanation",
        "briefl", "summarize it", "what about it", "tell about it"
    ]

    existing_doc_ids = json.loads(session.doc_ids or "[]") if session else []
    new_doc_ids = req.uploaded_doc_ids or []
    all_session_doc_ids = list(set(existing_doc_ids + new_doc_ids))

    if new_doc_ids and set(new_doc_ids) != set(existing_doc_ids):
        session.doc_ids = json.dumps(all_session_doc_ids)
        db.commit()

    if (all_session_doc_ids and not history and any(p in q_lower for p in vague)):
        question = "Summarize this document completely — explain all topics, key concepts, and important points."

    source_filter = []
    if all_session_doc_ids:
        source_filter = _get_session_doc_names(db, current_user.id, all_session_doc_ids)

    all_ready = _get_all_user_ready_docs(db, current_user.id)
    total_docs = db.query(Document).filter(Document.user_id == current_user.id).count()
    processing_docs = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.is_indexed == 0
    ).count()

    if total_docs == 0:
        result = {
            "answer": "📂 **No documents uploaded yet.**\n\nPlease upload a PDF using the 📎 button, then ask your question!",
            "sources": []
        }

    elif len(all_ready) == 0 and processing_docs > 0:
        result = {
            "answer": "⏳ **Your PDF is still being processed...**\n\nPlease wait a moment and try again. The Send button will unlock automatically when ready!",
            "sources": []
        }

    else:
        retrieval_k = TOP_K_RESULTS
        if query_type in ["summary", "predict"]:
            # For one-night exam prep style requests, pull broader context
            # to avoid missing major topics from the selected PDF(s).
            retrieval_k = max(TOP_K_RESULTS * 3, 25)

        chunks = query_user_index(
            current_user.id,
            question,
            top_k=retrieval_k,
            source_filter=source_filter
        )

        if not chunks and not is_followup:
            searched = ", ".join(source_filter) if source_filter else "your uploaded PDF(s)"
            result = {
                "answer": (
                    "❌ **This is not mentioned in the uploaded PDF content.**\n\n"
                    f"Searched in: {searched}\n\n"
                    "I only answer from your uploaded PDF(s). "
                    "If you want, I can give a short general explanation separately, but it will be outside-PDF guidance."
                ),
                "sources": []
            }
        else:
            try:
                result = answer_question(
                    chunks,
                    question,
                    conversation_context=conv_context,
                    is_followup=is_followup
                )
            except Exception as e:
                print(f"[QA Error] {e}")
                result = {
                    "answer": (
                        "⚠️ **AI service is currently busy or temporarily unavailable.**\n\n"
                        "Your document was uploaded and indexed correctly, but the answer generation service "
                        "is under high load right now.\n\n"
                        "👉 Please try again in a few moments."
                    ),
                    "sources": []
                }

    clean_sources = [_clean_filename(s) for s in result.get("sources", [])]

    chat = ChatHistory(
        user_id=current_user.id,
        session_id=session_id,
        question=req.question,
        answer=result["answer"],
        sources=json.dumps(clean_sources)
    )
    db.add(chat)
    db.commit()

    return {
        "question": req.question,
        "answer": result["answer"],
        "sources": clean_sources,
        "session_id": session_id,
        "is_followup": is_followup
    }


@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: int,
                         current_user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(404, "Session not found")

    chats = db.query(ChatHistory).filter(
        ChatHistory.session_id == session_id
    ).order_by(ChatHistory.created_at).all()

    return [{
        "id": c.id,
        "question": c.question,
        "answer": c.answer,
        "sources": json.loads(c.sources) if c.sources else [],
        "created_at": c.created_at.isoformat()
    } for c in chats]


@router.get("/history")
def get_history(current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    chats = db.query(ChatHistory).filter(
        ChatHistory.user_id == current_user.id
    ).order_by(ChatHistory.created_at.desc()).limit(50).all()

    return [{
        "id": c.id,
        "question": c.question,
        "answer": c.answer,
        "sources": json.loads(c.sources) if c.sources else [],
        "created_at": c.created_at.isoformat()
    } for c in chats]


@router.delete("/history")
def clear_history(current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    db.query(ChatHistory).filter(ChatHistory.user_id == current_user.id).delete()
    db.query(ChatSession).filter(ChatSession.user_id == current_user.id).delete()
    db.commit()
    return {"message": "All cleared"}


class EvaluateRequest(BaseModel):
    question: str
    doc_ids: Optional[List[int]] = None


@router.post("/evaluate")
def evaluate_answer(
    req: EvaluateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lightweight RAG evaluation endpoint.
    Retrieves context for the question, generates an answer,
    then scores it on context relevance, faithfulness, and completeness.
    Useful for demonstrating system quality in reports/presentations.
    """
    if not req.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    source_filter = []
    if req.doc_ids:
        docs = db.query(Document).filter(
            Document.id.in_(req.doc_ids),
            Document.user_id == current_user.id,
            Document.is_indexed == 1
        ).all()
        source_filter = [_clean_filename(d.filename) for d in docs]

    chunks = query_user_index(
        current_user.id, req.question, top_k=8, source_filter=source_filter
    )
    if not chunks:
        return {
            "error": "No indexed content found. Upload and index a document first.",
            "scores": None
        }

    try:
        result = answer_question(chunks, req.question)
        answer = result.get("answer", "")
    except Exception as e:
        return {"error": f"Answer generation failed: {e}", "scores": None}

    scores = evaluate_qa_pair(req.question, answer, chunks)
    return {
        "question":       req.question,
        "answer_preview": answer[:400] + ("..." if len(answer) > 400 else ""),
        "sources_used":   result.get("sources", []),
        "scores":         scores
    }