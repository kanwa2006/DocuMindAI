"""Regression tests for DEBUG_MASTER_PLAN H-1.

VECTOR_BACKEND defaulted to "faiss", whose branch is an in-memory NumPy
scan (FAISS was imported but never used and is not a dependency). The
default is now pgvector, backed by an HNSW index migration.
"""
import pathlib

from app.core.config import Settings


def test_vector_backend_class_default_is_pgvector():
    assert Settings.model_fields["VECTOR_BACKEND"].default == "pgvector"


def test_hnsw_index_migration_exists():
    versions = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"
    migration = versions / "d0aab53082d2_add_hnsw_index_document_chunks_embedding.py"
    assert migration.exists()
    text = migration.read_text(encoding="utf-8")
    assert "USING hnsw" in text
    assert "vector_cosine_ops" in text  # must match cosine_distance in retrieval
    assert "document_chunks" in text


def test_faiss_import_removed_from_retrieval_service():
    """The misleading guarded `import faiss` is gone (it was never used)."""
    import re

    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "app" / "services" / "retrieval_service.py"
    ).read_text(encoding="utf-8")
    assert not re.search(r"^\s*import faiss", source, re.MULTILINE)
