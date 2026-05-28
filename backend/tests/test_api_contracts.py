import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health_check():
    """Validates the core application REST startup contract."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

@pytest.mark.asyncio
async def test_docs_schema_generation():
    """Validates that OpenAPI schema can generate without breaking."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/openapi.json")
    assert response.status_code == 200
