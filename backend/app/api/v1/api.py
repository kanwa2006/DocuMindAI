from fastapi import APIRouter
from app.api.v1.endpoints import (
    health, documents, query, export, benchmark, exams,
    hr, legal, finance, study, research, ws, auth, csrf, chats,
    corrections, retention, reports,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(benchmark.router, prefix="/benchmark", tags=["benchmark"])
api_router.include_router(exams.router, prefix="/exams", tags=["exams"])
api_router.include_router(hr.router, prefix="/hr", tags=["hr"])
api_router.include_router(legal.router, prefix="/legal", tags=["legal"])
api_router.include_router(finance.router, prefix="/finance", tags=["finance"])
api_router.include_router(study.router, prefix="/study", tags=["study"])
api_router.include_router(research.router, prefix="/research", tags=["research"])
api_router.include_router(ws.router, tags=["websocket"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(csrf.router, tags=["csrf"])
api_router.include_router(chats.router, prefix="/chats", tags=["chats"])
api_router.include_router(corrections.router, prefix="/corrections", tags=["corrections"])
# Phase 9-E: Workflow retention (templates, notifications, change-detection, schedules)
api_router.include_router(retention.router, tags=["retention"])
# Phase 9-F: Distribution (reports, share links, message notes, doc naming)
api_router.include_router(reports.router, tags=["reports"])
