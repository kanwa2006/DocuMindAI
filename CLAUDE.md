## HIGH-RISK CORE SYSTEMS

These systems are production-critical.

Prefer additive fixes and wrappers first.

Do NOT rewrite internals unless:

* runtime verification proves the subsystem is the root cause
* the issue cannot be fixed externally
* the change is minimal and production-safe

High-risk files:

* backend/app/services/retrieval_service.py
* backend/app/services/grounding_service.py
* backend/app/services/chunking_service.py
* backend/app/workers/celery_app.py
* backend/app/workers/tasks/hr_tasks.py

Any modification to high-risk systems MUST include:

* exact root cause
* affected execution path
* regression risks
* runtime verification using real uploads and real outputs

## MANDATORY RUNTIME VERIFICATION

Do NOT claim a subsystem works unless verified using:

* real uploads
* real retrieval
* real citations
* real compare-mode outputs
* real streaming responses
* real structured generation

Do NOT trust:

* API 200 responses
* rendered UI
* placeholder trust scores
* mock outputs
* generic “system operational” responses

For every fix:

1. reproduce the issue
2. identify exact root cause
3. apply minimal production-grade fix
4. verify with real uploads
5. document remaining failures honestly

Never generate fake “everything passed” audit reports.
