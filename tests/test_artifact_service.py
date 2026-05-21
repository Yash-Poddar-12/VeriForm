"""Tests for Artifact Service."""

import pytest
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from veriform.persistence.database import Base
from veriform.services.artifact_service import ArtifactService
from veriform.services.services import ExecutionService
import zipfile
import os

@pytest.fixture
async def artifact_db(monkeypatch, tmp_path):
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
    monkeypatch.setattr("veriform.services.artifact_service.get_session", mock_get_session)
    
    from veriform.config import settings
    monkeypatch.setattr(settings, "artifact_storage_dir", tmp_path)
    
    yield engine
    await engine.dispose()

@pytest.mark.asyncio
async def test_artifact_service(artifact_db, tmp_path):
    exec_svc = ExecutionService()
    run = await exec_svc.create_run("http://test.com")
    
    art_svc = ArtifactService()
    
    art1 = await art_svc.store_screenshot(run.id, "hash1", b"fakeimage")
    assert art1.artifact_type == "screenshot"
    assert os.path.exists(art1.storage_path)
    
    art2 = await art_svc.store_trace_log(run.id, ['{"type": "action"}'])
    assert art2.artifact_type == "trace"
    assert os.path.exists(art2.storage_path)
    
    zip_path = await art_svc.export_run_bundle(run.id)
    assert os.path.exists(zip_path)
    
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert any("screenshot" in name for name in namelist)
        assert any("trace.jsonl" in name for name in namelist)
