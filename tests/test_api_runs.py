"""Tests for FastAPI endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from veriform.api.app import app
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from veriform.persistence.database import Base
from unittest.mock import patch, AsyncMock

@pytest.fixture
async def api_db(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def mock_get_session():
        async with Session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
                
    monkeypatch.setattr("veriform.services.services.get_session", mock_get_session)
    yield engine
    await engine.dispose()

@pytest.fixture
async def client(api_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_create_and_get_run(client):
    with patch("veriform.api.routes.runs.task_queue.push", new_callable=AsyncMock) as mock_push:
        response = await client.post("/api/v1/runs/", json={"target_url": "http://example.com"})
        assert response.status_code == 202
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"
        
        run_id = data["id"]
        
        # Test get run
        res2 = await client.get(f"/api/v1/runs/{run_id}")
        assert res2.status_code == 200
        assert res2.json()["status"] == "pending"
        
        # Test list runs
        res3 = await client.get("/api/v1/runs/")
        assert res3.status_code == 200
        assert len(res3.json()) >= 1
