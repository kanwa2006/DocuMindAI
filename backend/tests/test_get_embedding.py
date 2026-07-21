"""Regression tests for DEBUG_MASTER_PLAN C-1.

`llm_service.get_embedding` was called from 12 sites (four `*/search`
endpoints and four worker task modules) but never defined, so every call
raised AttributeError. These tests pin the method's existence and its
contract: an async method returning a 1024-dim vector routed through
`embedding_service`.
"""
import asyncio
from unittest.mock import patch

import pytest

from app.services.llm_service import LLMService, llm_service
from app.services.embedding_service import EMBEDDING_DIM


def test_get_embedding_exists():
    """C-1: the method must exist on LLMService and on the singleton."""
    assert hasattr(LLMService, "get_embedding")
    assert callable(getattr(llm_service, "get_embedding", None))


@pytest.mark.asyncio
async def test_get_embedding_returns_1024_dim_vector():
    """The returned vector must match the DB Vector(1024) column dimension."""
    fake_vector = [0.1] * EMBEDDING_DIM
    with patch(
        "app.services.embedding_service.embedding_service.generate_embeddings",
        return_value=[fake_vector],
    ) as mock_gen:
        result = await llm_service.get_embedding("test query")

    mock_gen.assert_called_once_with(["test query"])
    assert isinstance(result, list)
    assert len(result) == EMBEDDING_DIM
    assert result == fake_vector


@pytest.mark.asyncio
async def test_get_embedding_raises_on_empty_result():
    """No silent fallback: an empty provider result must raise, not degrade."""
    with patch(
        "app.services.embedding_service.embedding_service.generate_embeddings",
        return_value=[],
    ):
        with pytest.raises(ValueError):
            await llm_service.get_embedding("test query")
