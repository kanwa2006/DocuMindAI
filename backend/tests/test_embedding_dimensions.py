"""Regression tests for DEBUG_MASTER_PLAN C-7 (newly discovered).

Every workspace embedding column was declared vector(1536) (OpenAI-ada-era
scaffold) while the pipeline produces 1024-dim vectors (bge-m3), so inserts
and l2_distance comparisons would fail at the DB layer even after C-1/C-2.
Pins all embedding columns to EMBEDDING_DIM.
"""
import pytest

from app.services.embedding_service import EMBEDDING_DIM
from app.models.document_chunk import DocumentChunk
from app.models.hr import CandidateProfile
from app.models.legal import Clause
from app.models.finance import Transaction
from app.models.study import StudyNote, Flashcard
from app.models.research import ResearchPaper, ResearchFinding

EMBEDDING_MODELS = [
    DocumentChunk, CandidateProfile, Clause, Transaction,
    StudyNote, Flashcard, ResearchPaper, ResearchFinding,
]


@pytest.mark.parametrize("model", EMBEDDING_MODELS, ids=lambda m: m.__name__)
def test_embedding_column_matches_pipeline_dimension(model):
    column = model.__table__.columns["embedding"]
    assert column.type.dim == EMBEDDING_DIM, (
        f"{model.__name__}.embedding is vector({column.type.dim}) but the "
        f"embedding pipeline produces {EMBEDDING_DIM}-dim vectors"
    )
