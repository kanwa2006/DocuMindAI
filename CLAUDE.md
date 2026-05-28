# DocuMindAI — Claude Code Guide

## STABLE SYSTEMS — DO NOT MODIFY AFTER CREATION

These files were carefully built and stabilised. Make only additive/wrapper changes; never rewrite internals.

| File | Phase | Notes |
|------|-------|-------|
| `backend/app/services/llm_key_rotation.py` | Phase 12 | GeminiKeyRotator singleton — STABLE after creation |
| `backend/app/services/llm_service.py` | Phase 7 | Wrap only; never rewrite provider internals |
| `backend/app/services/veritas_engine.py` | Phase 18 | STABLE after creation |
| `backend/app/automation/auto_health_check.py` | Phase 20 | STABLE after creation |
| `backend/app/automation/auto_daily_digest.py` | Phase 20 | STABLE after creation |

Files that must **never** be modified regardless of phase:
- `backend/app/services/retrieval_service.py`
- `backend/app/services/grounding_service.py`
- `backend/app/services/chunking_service.py`
- `backend/app/workers/celery_app.py`
- `backend/app/workers/tasks/hr_tasks.py`

## Phase 12 — API Key Rotation

Keys are loaded from `.env` at startup by `GeminiKeyRotator`.  
**To add a key:** add `GEMINI_API_KEY_2=...` (or `_3`, `_4`, ...) to `.env` and restart. No code changes.

```
GEMINI_API_KEY_1=...   # required
GEMINI_API_KEY_2=...   # optional — uncomment to enable rotation
```

Health check: `GET /api/v1/health/detailed` → `api_keys.total / available / exhausted / invalid`
