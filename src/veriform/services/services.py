"""
veriform.services.services
==========================
Service layer encapsulating business logic.
Coordinates repositories and orchestrator/executor components.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from veriform.models.schemas import RunSummarySchema
from veriform.models.workflow import WorkflowSession
from veriform.persistence.database import get_session
from veriform.persistence.models import WorkflowRun
from veriform.persistence.repositories import (
    ArtifactRepository,
    RunRepository,
    WorkflowRepository,
)


class WorkflowService:
    """Manages workflow persistence and graph reconstruction."""

    async def persist_session(self, session_data: WorkflowSession) -> None:
        """Persist a completed WorkflowSession into the database."""
        async with get_session() as db:
            run_repo = RunRepository(db)
            wf_repo = WorkflowRepository(db)
            
            # Find the run
            run = await run_repo.get_run(session_data.run_id)
            if not run:
                raise ValueError(f"Run {session_data.run_id} not found.")

            # Persist nodes
            for state_hash, node in session_data.graph_nodes.items():
                snap = session_data.snapshots.get(state_hash)
                snapshot_dict = snap.model_dump(mode="json") if snap else None
                await wf_repo.add_state(
                    run_id=run.id,
                    state_hash=state_hash,
                    url=node.first_seen_url,
                    is_terminal=node.is_terminal,
                    snapshot=snapshot_dict
                )
                
                # Persist transitions
                for edge in node.edges_out:
                    await wf_repo.add_transition(
                        run_id=run.id,
                        from_hash=edge.from_state_hash,
                        to_hash=edge.to_state_hash,
                        action_type=edge.action_taken.type,
                        action_payload=edge.action_taken.model_dump(mode="json"),
                        status=edge.result.status if edge.result else "unknown",
                    )
                    
            # Persist events
            for action in session_data.action_timeline:
                await wf_repo.log_event(
                    run_id=run.id,
                    event_type="action_executed",
                    payload=action.model_dump(mode="json")
                )


class ExecutionService:
    """Manages launching, tracking, and canceling test runs."""

    # We will expand this when the Queue system is implemented in Phase 5.
    
    async def create_run(self, target_url: str) -> WorkflowRun:
        async with get_session() as db:
            repo = RunRepository(db)
            return await repo.create_run(target_url)

    async def update_status(self, run_id: str, status: str, duration_ms: Optional[int] = None) -> None:
        async with get_session() as db:
            repo = RunRepository(db)
            await repo.update_run_status(run_id, status, duration_ms)

    async def get_run_details(self, run_id: str) -> Optional[WorkflowRun]:
        async with get_session() as db:
            repo = RunRepository(db)
            return await repo.get_run(run_id, include_details=True)
            
    async def list_runs(self, limit: int = 50, offset: int = 0) -> list[WorkflowRun]:
        async with get_session() as db:
            repo = RunRepository(db)
            return list(await repo.list_runs(limit, offset))


class ReplayService:
    """Service to reconstruct replay timelines and traces."""

    async def get_replay_events(self, run_id: str) -> List[Dict[str, Any]]:
        """Fetch deterministic event timeline for a run."""
        async with get_session() as db:
            run_repo = RunRepository(db)
            run = await run_repo.get_run(run_id, include_details=True)
            if not run:
                return []
            
            events = []
            for ev in run.events:
                events.append({
                    "id": ev.id,
                    "type": ev.event_type,
                    "timestamp": ev.timestamp.isoformat(),
                    "payload": ev.payload
                })
            
            # Sort by timestamp
            events.sort(key=lambda x: x["timestamp"])
            return events
