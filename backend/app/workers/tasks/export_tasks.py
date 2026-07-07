import asyncio
import uuid
import logging
from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.legal import Contract, Clause
from app.services.export_engine import export_engine
from app.core.storage import storage_service
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

async def _process_async_export(contract_id: str, job_id: str):
    """
    PHASE 4: EXPORT QUEUE SYSTEM
    Offloads heavy DOCX generation from the API layer to Celery.
    """
    async with AsyncSessionLocal() as db:
        logger.info(f"Starting async export job {job_id} for contract {contract_id}")
        
        stmt = select(Contract).where(Contract.id == contract_id).options(
            selectinload(Contract.clauses).selectinload(Clause.redlines)
        )
        contract = (await db.execute(stmt)).scalar_one_or_none()
        
        if not contract:
            logger.error(f"Export Job {job_id} failed: Contract not found")
            return

        clauses_data = []
        for clause in contract.clauses:
            c_data = {
                "clause": {
                    "section_name": clause.section_name,
                    "original_text": clause.original_text,
                    "risk_level": clause.risk_level,
                    "compliance_notes": clause.compliance_notes
                },
                "redlines": [{"suggested_text": r.suggested_text} for r in clause.redlines]
            }
            clauses_data.append(c_data)

        try:
            file_stream = export_engine.generate_legal_redline_docx(contract.title, clauses_data)
            
            # Centralized storage reconciliation
            file_url = storage_service.save_file_stream_sync(file_stream, f'exports/{job_id}.docx')
            
            # Update ExportJob status to COMPLETE and save file_url
            logger.info(f"Export Job {job_id} complete. Available at {file_url}")
            
            # Trigger WebSocket broadcast notifying user the export is ready
            # redis_pubsub.publish(channel=contract.workspace_id, message={"type": "export_ready", "url": file_url})
            
        except Exception as e:
            logger.error(f"Export Job {job_id} failed: {e}")
            raise


@celery_app.task(name="app.workers.tasks.export_tasks.process_export_job", bind=True)
def process_export_job(self, contract_id: str, job_id: str):
    try:
        asyncio.run(_process_async_export(contract_id, job_id))
    except Exception as exc:
        logger.error(f"Failed to process export {job_id}. Retrying...")
        self.retry(exc=exc, countdown=15, max_retries=3)
