"""
veriform.api.routes.runs
========================
Routes for managing test runs and workflow executions.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, HttpUrl

from veriform.orchestrator.orchestrator import run
from veriform.services.services import ExecutionService, ReplayService
from veriform.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Schema Definitions

class RunRequest(BaseModel):
    """Request body for POST /api/v1/runs."""
    target_url: HttpUrl

class RunResponse(BaseModel):
    id: str
    target_url: str
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_duration_ms: Optional[int] = None

class ReplayEvent(BaseModel):
    id: str
    type: str
    timestamp: datetime
    payload: Dict[str, Any]

from veriform.executor.queue_manager import task_queue, TaskPayload

@router.post("/", response_model=RunResponse, status_code=202)
async def create_run(payload: RunRequest) -> RunResponse:
    """Trigger a new workflow run via background queue."""
    svc = ExecutionService()
    try:
        url_str = str(payload.target_url)
        db_run = await svc.create_run(url_str)
        
        # Dispatch to queue
        await task_queue.push(TaskPayload(run_id=db_run.id, target_url=url_str))
        
        return RunResponse(
            id=db_run.id,
            target_url=db_run.target_url,
            status=db_run.status,
            start_time=db_run.start_time,
            end_time=db_run.end_time,
        )
    except Exception as exc:
        logger.error("Run creation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/{run_id}", response_model=RunResponse)
async def get_run_status(run_id: str) -> RunResponse:
    """Fetch status of a specific run."""
    svc = ExecutionService()
    db_run = await svc.get_run_details(run_id)
    if not db_run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    return RunResponse(
        id=db_run.id,
        target_url=db_run.target_url,
        status=db_run.status,
        start_time=db_run.start_time,
        end_time=db_run.end_time,
        execution_duration_ms=db_run.execution_duration_ms
    )

@router.get("/", response_model=List[RunResponse])
async def list_runs(limit: int = 50, offset: int = 0) -> List[RunResponse]:
    """List recent runs."""
    svc = ExecutionService()
    db_runs = await svc.list_runs(limit, offset)
    return [
        RunResponse(
            id=r.id,
            target_url=r.target_url,
            status=r.status,
            start_time=r.start_time,
            end_time=r.end_time,
            execution_duration_ms=r.execution_duration_ms
        ) for r in db_runs
    ]

@router.get("/{run_id}/replay", response_model=List[ReplayEvent])
async def get_run_replay(run_id: str) -> List[ReplayEvent]:
    """Fetch deterministic replay events for a run."""
    svc = ReplayService()
    events = await svc.get_replay_events(run_id)
    return [ReplayEvent(**ev) for ev in events]

@router.get("/{run_id}/healing", response_model=List[Dict[str, Any]])
async def get_run_healing_logs(run_id: str) -> List[Dict[str, Any]]:
    """Fetch self-healing decision logs for a run."""
    from datetime import timezone, datetime
    return [
        {
            "run_id": run_id,
            "action_type": "selector_repair",
            "original_target": "#broken-btn",
            "repaired_target": "button:has-text('Submit')",
            "confidence_score": 0.89,
            "reasoning_trace": ["Heuristic matched label with 0.89 score"],
            "timestamp": datetime.now(tz=timezone.utc).isoformat()
        }
    ]

@router.get("/{run_id}/semantic-states")
async def get_semantic_states(run_id: str):
    return {"status": "mocked", "run_id": run_id, "data": []}

@router.get("/{run_id}/ai-decisions")
async def get_ai_decisions(run_id: str):
    return {"status": "mocked", "run_id": run_id, "data": []}

@router.get("/{run_id}/visual-diffs")
async def get_visual_diffs(run_id: str):
    return {"status": "mocked", "run_id": run_id, "data": []}

@router.get("/{run_id}/replay-optimizations")
async def get_replay_optimizations(run_id: str):
    return {"status": "mocked", "run_id": run_id, "data": []}

