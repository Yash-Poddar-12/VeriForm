"""
veriform.api.routes.runs
========================
Route: POST /runs

Accepts a target URL and triggers a synchronous test run via the orchestrator.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from veriform.models.schemas import RunSummarySchema
from veriform.orchestrator.orchestrator import OrchestratorError, run
from veriform.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class RunRequest(BaseModel):
    """Request body for POST /runs."""

    target_url: HttpUrl


@router.post("/", response_model=RunSummarySchema, status_code=202)
async def create_run(payload: RunRequest) -> RunSummarySchema:
    """Trigger a form test run against *payload.target_url*.

    Returns the ``RunSummarySchema`` once the run completes.

    TODO (Phase 1):
        - Add background task support so the client can poll for results.
        - Return 202 immediately with a run_id, stream progress via SSE.
    """
    try:
        logger.info("POST /runs – target_url=%s", payload.target_url)
        summary = await run(str(payload.target_url))
        return summary
    except OrchestratorError as exc:
        logger.error("Run failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
