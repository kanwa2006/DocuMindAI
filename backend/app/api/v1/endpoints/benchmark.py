from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Any
import uuid

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.benchmark_run import BenchmarkRun
from app.schemas.benchmark import BenchmarkRunCreate, BenchmarkRunResponse
from app.services.evaluation_service import EvaluationService

router = APIRouter()

@router.post("", response_model=BenchmarkRunResponse)
async def create_benchmark_run(
    request: BenchmarkRunCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a deterministic retrieval benchmark suite and persist metrics.
    """
    workspace_id = uuid.UUID(current_user["workspace_id"])
    
    # Run evaluation suite
    eval_report = await EvaluationService.run_benchmark(
        db=db,
        workspace_id=workspace_id,
        queries=[q.model_dump() for q in request.queries]
    )
    
    run_record = BenchmarkRun(
        workspace_id=workspace_id,
        name=request.name,
        mrr_before_rerank=eval_report["mrr_before_rerank"],
        mrr_after_rerank=eval_report["mrr_after_rerank"],
        avg_latency_sec=eval_report["avg_latency_sec"],
        results=eval_report["results"]
    )
    db.add(run_record)
    await db.commit()
    await db.refresh(run_record)
    
    return run_record

@router.get("", response_model=List[BenchmarkRunResponse])
async def list_benchmark_runs(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Fetch benchmark history for the active workspace."""
    workspace_id = uuid.UUID(current_user["workspace_id"])
    stmt = select(BenchmarkRun).where(BenchmarkRun.workspace_id == workspace_id).order_by(BenchmarkRun.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()
