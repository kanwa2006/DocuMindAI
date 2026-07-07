import pytest
from httpx import AsyncClient
from app.main import app
from app.core.config import settings
from unittest.mock import patch, MagicMock

try:
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
except ImportError:
    transport = None

@pytest.mark.asyncio
async def test_health_check():
    """Validates the core application REST startup contract."""
    with patch("app.api.v1.endpoints.health._db_ping") as mock_ping, \
         patch("app.api.v1.endpoints.health.redis.from_url") as mock_redis_from_url:
        
        # mock redis client
        mock_redis = MagicMock()
        async def mock_ping_async():
            return True
        async def mock_close_async():
            return None
        mock_redis.ping = mock_ping_async
        mock_redis.close = mock_close_async
        mock_redis_from_url.return_value = mock_redis
        
        # mock db_ping as a success (does nothing)
        mock_ping.return_value = None

        if transport:
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get("/api/v1/health")
        else:
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["api"] == "ok"

@pytest.mark.asyncio
async def test_docs_schema_generation():
    """Validates that OpenAPI schema can generate without breaking."""
    if transport:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(f"{settings.API_V1_STR}/openapi.json")
    else:
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(f"{settings.API_V1_STR}/openapi.json")
    assert response.status_code == 200

