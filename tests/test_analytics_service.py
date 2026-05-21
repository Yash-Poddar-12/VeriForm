"""Tests for Analytics Service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from veriform.persistence.database import Base
from veriform.services.analytics_service import AnalyticsService
from veriform.persistence.repositories import RunRepository, WorkflowRepository

@pytest.fixture
async def analytics_db(monkeypatch):
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
                
    monkeypatch.setattr("veriform.services.analytics_service.get_session", mock_get_session)
    
    # Create two runs with different states
    async with Session() as session:
        run_repo = RunRepository(session)
        wf_repo = WorkflowRepository(session)
        
        run_a = await run_repo.create_run("http://test.com")
        await wf_repo.add_state(run_a.id, "hash1", "http://test.com", False)
        await wf_repo.add_state(run_a.id, "hash2", "http://test.com/2", False)
        await wf_repo.add_transition(run_a.id, "hash1", "hash2", "click", {}, "success")
        
        run_b = await run_repo.create_run("http://test.com")
        await wf_repo.add_state(run_b.id, "hash1", "http://test.com", False)
        # Missing hash2, added hash3
        await wf_repo.add_state(run_b.id, "hash3", "http://test.com/3", False)
        await wf_repo.add_transition(run_b.id, "hash1", "hash3", "fill", {}, "success")
        
        await session.commit()
        
    yield engine, run_a.id, run_b.id
    await engine.dispose()

@pytest.mark.asyncio
async def test_analytics_service(analytics_db):
    engine, run_a_id, run_b_id = analytics_db
    svc = AnalyticsService()
    
    report = await svc.get_regression_report("http://test.com", run_a_id, run_b_id)
    
    assert report["states_discovered_a"] == 2
    assert report["states_discovered_b"] == 2
    assert "hash2" in report["missing_states"]
    assert "hash3" in report["new_states"]
    assert report["has_regression"] is True
