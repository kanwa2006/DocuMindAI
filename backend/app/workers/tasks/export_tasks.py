"""Legal redline DOCX export (Celery).

P0-7: used `AsyncSessionLocal` in a sync Celery task via `asyncio.run()`, so a
pooled asyncpg connection from a previous event loop failed intermittently with
"got Future attached to a different loop". Now `SyncSessionLocal`.

Separately broken, independent of P0-7: the query eager-loaded
`selectinload(Contract.clauses).selectinload(Clause.redlines)`, but **neither
relationship exists** — `app/models/legal.py` declares only the foreign-key
columns. Any dispatch raised `AttributeError` before touching the database.
Clauses and redlines are now fetched with explicit queries rather than by adding
relationships, keeping the change inside this task instead of altering shared
models every workspace imports.

P0-9: `Contract`, `Clause` and `RedlineSuggestion` are `TenantScoped`, so this
task must establish an owner scope or every read raises `TenantScopeMissing`.
The contract's owner is resolved once under `system_scope()` — a deliberate,
narrow bootstrap, because a background job has no request to inherit scope from
— and all subsequent reads run under that owner. Authorization to export
belongs to the dispatching endpoint; this task trusts the contract_id it is
given, exactly as it trusted it before.
"""
import logging
import uuid

from sqlalchemy.future import select

from app.core.storage import storage_service
from app.core.tenant_scope import system_scope, tenant_scope
from app.db.session import SyncSessionLocal
from app.models.legal import Clause, Contract, RedlineSuggestion
from app.services.export_engine import export_engine
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _process_export(contract_id: str, job_id: str) -> None:
    """PHASE 4: EXPORT QUEUE — offloads DOCX generation from the API layer."""
    db = SyncSessionLocal()
    try:
        logger.info("Starting export job %s for contract %s", job_id, contract_id)

        # Bootstrap: resolve the contract's owner so the rest of the task can run
        # under a real tenant scope. Kept as narrow as possible.
        with system_scope():
            contract = db.execute(
                select(Contract).where(Contract.id == contract_id)
            ).scalar_one_or_none()

        if not contract:
            logger.error("Export job %s failed: contract %s not found", job_id, contract_id)
            return

        with tenant_scope(contract.owner_id):
            clauses = (
                db.execute(
                    select(Clause)
                    .where(Clause.contract_id == contract.id)
                    .order_by(Clause.created_at)
                )
                .scalars()
                .all()
            )

            clauses_data = []
            for clause in clauses:
                redlines = (
                    db.execute(
                        select(RedlineSuggestion).where(
                            RedlineSuggestion.clause_id == clause.id
                        )
                    )
                    .scalars()
                    .all()
                )
                clauses_data.append(
                    {
                        "clause": {
                            "section_name": clause.section_name,
                            "original_text": clause.original_text,
                            "risk_level": clause.risk_level,
                            "compliance_notes": clause.compliance_notes,
                        },
                        "redlines": [
                            {"suggested_text": r.suggested_text} for r in redlines
                        ],
                    }
                )

            file_stream = export_engine.generate_legal_redline_docx(
                contract.title, clauses_data
            )
            file_url = storage_service.save_file_stream_sync(
                file_stream, f"exports/{job_id}.docx"
            )
            logger.info(
                "Export job %s complete — %d clauses. Available at %s",
                job_id,
                len(clauses_data),
                file_url,
            )
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.export_tasks.process_export_job", bind=True)
def process_export_job(self, contract_id: str, job_id: str):
    try:
        uuid.UUID(contract_id)  # fail fast on a malformed id rather than mid-export
        _process_export(contract_id, job_id)
    except Exception as exc:
        logger.error("Failed to process export %s. Retrying...", job_id)
        self.retry(exc=exc, countdown=15, max_retries=3)
