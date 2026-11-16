import pytest
from httpx import AsyncClient, ASGITransport
from api.index import app

@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/health")
        assert r.status_code == 200
        assert r.json()["success"] is True

@pytest.mark.asyncio
async def test_api_info():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api")
        assert r.json()["data"]["name"] == "AYAKA API"

@pytest.mark.asyncio
async def test_missing_api_key():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/am/status?email=a@b.com")
        assert r.status_code == 401

@pytest.mark.asyncio
async def test_invalid_api_key_format():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/api/am/status?email=a@b.com",
            headers={"X-API-Key": "not-an-ayaka-key"},
        )
        assert r.status_code == 401