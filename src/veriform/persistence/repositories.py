"""
veriform.persistence.repositories
=================================
Repository layer for accessing workflow execution data.
Strictly separates business logic from SQL/ORM specifics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from veriform.persistence.models import (
    ExecutionEvent,
    WorkflowArtifact,
    WorkflowRun,
    WorkflowState,
    WorkflowTransition,
)


class RunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_run(self, target_url: str) -> WorkflowRun:
        run = WorkflowRun(target_url=target_url, status="pending")
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_run(self, run_id: str, include_details: bool = False) -> Optional[WorkflowRun]:
        stmt = select(WorkflowRun).where(WorkflowRun.id == run_id)
        if include_details:
            stmt = stmt.options(
                selectinload(WorkflowRun.states),
                selectinload(WorkflowRun.transitions),
                selectinload(WorkflowRun.events),
                selectinload(WorkflowRun.artifacts),
            )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_run_status(self, run_id: str, status: str, duration_ms: Optional[int] = None) -> None:
        run = await self.get_run(run_id)
        if run:
            run.status = status
            if duration_ms is not None:
                run.execution_duration_ms = duration_ms
            await self.session.flush()

    async def list_runs(self, limit: int = 50, offset: int = 0) -> Sequence[WorkflowRun]:
        stmt = select(WorkflowRun).order_by(WorkflowRun.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class WorkflowRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_state(self, run_id: str, state_hash: str, url: str, is_terminal: bool, snapshot: Optional[Dict[str, Any]] = None) -> WorkflowState:
        # Check if state already exists for this run
        stmt = select(WorkflowState).where(WorkflowState.run_id == run_id, WorkflowState.state_hash == state_hash)
        result = await self.session.execute(stmt)
        state = result.scalar_one_or_none()
        
        if state:
            state.visit_count += 1
        else:
            state = WorkflowState(
                run_id=run_id,
                state_hash=state_hash,
                first_seen_url=url,
                is_terminal=is_terminal,
                visit_count=1,
                state_snapshot=snapshot,
            )
            self.session.add(state)
            
        await self.session.flush()
        return state

    async def add_transition(
        self, run_id: str, from_hash: str, to_hash: str, action_type: str, action_payload: Dict[str, Any], status: str
    ) -> WorkflowTransition:
        transition = WorkflowTransition(
            run_id=run_id,
            from_state_hash=from_hash,
            to_state_hash=to_hash,
            action_type=action_type,
            action_payload=action_payload,
            result_status=status,
        )
        self.session.add(transition)
        await self.session.flush()
        return transition
        
    async def log_event(self, run_id: str, event_type: str, payload: Dict[str, Any]) -> ExecutionEvent:
        event = ExecutionEvent(
            run_id=run_id,
            event_type=event_type,
            payload=payload,
        )
        self.session.add(event)
        await self.session.flush()
        return event


class ArtifactRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_artifact(self, run_id: str, artifact_type: str, storage_path: str) -> WorkflowArtifact:
        artifact = WorkflowArtifact(
            run_id=run_id,
            artifact_type=artifact_type,
            storage_path=storage_path,
        )
        self.session.add(artifact)
        await self.session.flush()
        return artifact

    async def get_artifacts_for_run(self, run_id: str) -> Sequence[WorkflowArtifact]:
        stmt = select(WorkflowArtifact).where(WorkflowArtifact.run_id == run_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
