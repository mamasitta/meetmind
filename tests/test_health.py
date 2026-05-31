# tests/test_health.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


class TestHealthEndpoint:
    
    @pytest.mark.asyncio
    async def test_health_returns_ok(self):
        """Test that /health endpoint works"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
    
    @pytest.mark.asyncio
    async def test_health_method_not_allowed(self):
        """Test that POST to /health returns 405"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post("/health")
            assert response.status_code == 405