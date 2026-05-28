import asyncio
import uuid
import logging
from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.legal import Contract, Clause, ComplianceRule, RedlineSuggestion
from app.models.document import Document
from app.schemas.legal import ContractSegmentationSchema, ClauseComplianceSchema
from app.services.llm_service import llm_service
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

async def _process_contract_logic(document_id: uuid.UUID, workspace_id: uuid.UUID):
    async with AsyncSessionLocal() as db:
        # 1. Setup & DB Fetch
        doc = (await db.execute(select(Document).where(Document.id == document_id))).scalar_one_or_none()
        if not doc:
            logger.error(f"Document {document_id} not found.")
            return

        rules = (await db.execute(select(ComplianceRule).where(ComplianceRule.workspace_id == workspace_id))).scalars().all()

        contract = Contract(
            workspace_id=workspace_id,
            document_id=document_id,
            title=f"Contract: {doc.filename}",
            status="IN_REVIEW"
        )
        db.add(contract)
        await db.flush()

        # 2. Extract & Segment (Simulated extraction of full text)
        logger.info(f"Segmenting contract {contract.id}")
        contract_text = f"Simulated text. 1. Confidentiality: Party agrees to never disclose secrets. 2. Liability: Liability capped at $50."
        
        # Security/Sanitization hook
        if "ignore previous instructions" in contract_text.lower():
            contract_text = "SANITIZED: Prompt injection detected."
            
        segmentation = await llm_service.generate_json(
            query="Segment this contract into individual clauses.",
            grounded_context=contract_text,
            response_schema=ContractSegmentationSchema
        )
        
        contract.party_name = segmentation.party_name
        contract.contract_type = segmentation.contract_type
        
        highest_risk = "LOW"
        
        # 3. Analyze Clauses
        for extracted_clause in segmentation.clauses:
            clause = Clause(
                workspace_id=workspace_id,
                contract_id=contract.id,
                section_name=extracted_clause.section_name,
                original_text=extracted_clause.original_text,
                clause_type=extracted_clause.clause_type,
                risk_level="COMPLIANT"
            )
            
            # PHASE 2: Generate Vector Embedding for Semantic Search
            clause.embedding = await llm_service.get_embedding(clause.original_text)
            
            db.add(clause)
            await db.flush()
            
            # PHASE 5: Advanced Compliance Rules
            for rule in rules:
                if rule.category == clause.clause_type or rule.category == "ALL":
                    evaluation = await llm_service.generate_json(
                        query=f"Evaluate this clause against the compliance rule: '{rule.rule_description}'.",
                        grounded_context=clause.original_text,
                        response_schema=ClauseComplianceSchema
                    )
                    
                    if not evaluation.is_compliant:
                        clause.risk_level = evaluation.risk_level
                        clause.compliance_notes = evaluation.compliance_notes
                        if evaluation.risk_level in ["HIGH", "MEDIUM"]:
                            highest_risk = "HIGH" if evaluation.risk_level == "HIGH" else ("MEDIUM" if highest_risk == "LOW" else highest_risk)
                        
                        if evaluation.needs_redline and evaluation.suggested_redline_text:
                            redline = RedlineSuggestion(
                                workspace_id=workspace_id,
                                clause_id=clause.id,
                                rule_id=rule.id,
                                suggested_text=evaluation.suggested_redline_text,
                                explanation=evaluation.compliance_notes
                            )
                            db.add(redline)

        contract.risk_score = highest_risk
        contract.status = "REVIEW_REQUIRED" if highest_risk == "HIGH" else "APPROVED"
        await db.commit()
        logger.info(f"Successfully processed contract {contract.id}")


@celery_app.task(name="app.workers.tasks.legal_tasks.process_contract_batch", bind=True)
def process_contract_batch(self, document_id: str, workspace_id: str):
    """
    PHASE 1: ASYNC LEGAL PROCESSING
    Offloads heavy compliance validation to Celery workers.
    """
    try:
        asyncio.run(_process_contract_logic(uuid.UUID(document_id), uuid.UUID(workspace_id)))
    except Exception as exc:
        logger.error(f"Failed to process contract {document_id}. Retrying...")
        self.retry(exc=exc, countdown=10)
