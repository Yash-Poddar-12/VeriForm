"""Tests for database repositories."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from veriform.persistence.database import Base
from veriform.persistence.repositories import RunRepository, WorkflowRepository, ArtifactRepository

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_run_repository(db_session):
    repo = RunRepository(db_session)
    run = await repo.create_run("http://test.com")
    
    assert run.id is not None
    assert run.target_url == "http://test.com"
    assert run.status == "pending"
    
    await repo.update_run_status(run.id, "running")
    
    fetched = await repo.get_run(run.id)
    assert fetched.status == "running"

@pytest.mark.asyncio
async def test_workflow_repository(db_session):
    repo = WorkflowRepository(db_session)
    
    run_repo = RunRepository(db_session)
    run = await run_repo.create_run("http://test.com")
    
    # Add state
    state1 = await repo.add_state(run.id, "hash1", "http://test.com", False)
    assert state1.visit_count == 1
    
    # Re-adding should increment visit_count
    state2 = await repo.add_state(run.id, "hash1", "http://test.com", False)
    assert state2.id == state1.id
    assert state2.visit_count == 2
    
    # Add transition
    txn = await repo.add_transition(run.id, "hash1", "hash2", "click", {"selector": "#btn"}, "success")
    assert txn.from_state_hash == "hash1"
    
    # Log event
    event = await repo.log_event(run.id, "click_started", {"target": "#btn"})
    assert event.event_type == "click_started"

@pytest.mark.asyncio
async def test_artifact_repository(db_session):
    repo = ArtifactRepository(db_session)
    
    run_repo = RunRepository(db_session)
    run = await run_repo.create_run("http://test.com")
    
    artifact = await repo.register_artifact(run.id, "screenshot", "/tmp/shot.png")
    
    artifacts = await repo.get_artifacts_for_run(run.id)
    assert len(artifacts) == 1
    assert artifacts[0].storage_path == "/tmp/shot.png"
