"""Tests for Service Layer."""

import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from veriform.persistence.database import Base
from veriform.services.services import ExecutionService, WorkflowService, ReplayService
from veriform.models.workflow import WorkflowSession, ActionSchema, WorkflowNode, TransitionSchema, StateSnapshot
import uuid
import unittest.mock

# We mock database.get_session to yield an in-memory session
@pytest.fixture
async def in_memory_db(monkeypatch):
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

@pytest.mark.asyncio
async def test_execution_service(in_memory_db):
    svc = ExecutionService()
    run = await svc.create_run("http://test.com")
    assert run.target_url == "http://test.com"
    assert run.status == "pending"
    
    await svc.update_status(run.id, "running", 1000)
    
    details = await svc.get_run_details(run.id)
    assert details.status == "running"
    assert details.execution_duration_ms == 1000
    
    runs = await svc.list_runs()
    assert len(runs) == 1

@pytest.mark.asyncio
async def test_workflow_service(in_memory_db):
    exec_svc = ExecutionService()
    run = await exec_svc.create_run("http://test.com")
    
    wf_svc = WorkflowService()
    
    # Create fake session data
    session_id = str(uuid.uuid4())
    session_data = WorkflowSession(
        session_id=session_id,
        run_id=run.id,
        start_time=datetime.now(tz=timezone.utc),
        graph_nodes={
            "hash1": WorkflowNode(state_hash="hash1", first_seen_url="http://test.com", is_terminal=True, edges_out=[])
        },
        action_timeline=[
            ActionSchema(action_id="a1", type="navigate", value="http://test.com")
        ]
    )
    
    await wf_svc.persist_session(session_data)
    
    replay_svc = ReplayService()
    events = await replay_svc.get_replay_events(run.id)
    
    assert len(events) == 1
    assert events[0]["payload"]["action_id"] == "a1"
