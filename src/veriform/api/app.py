"""
veriform.api.app
=================
FastAPI application factory and route registration.

Start the server:
    uvicorn veriform.api.app:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from veriform.api.routes import runs
from veriform.executor.queue_manager import task_queue, TaskPayload
from veriform.services.services import ExecutionService
async def _execute_task(payload: TaskPayload) -> None:
    from pathlib import Path
    from playwright.async_api import async_playwright
    from veriform.orchestrator.pipeline import PipelineOrchestrator
    from veriform.schemas.mutations import MutationProfile

    svc = ExecutionService()
    await svc.update_status(payload.run_id, "running")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            orchestrator = PipelineOrchestrator(
                page=page,
                run_id=payload.run_id,
                profile=MutationProfile.LIGHTWEIGHT
            )
            
            output_dir = Path("reports")
            await orchestrator.run(payload.target_url, output_dir)
            await browser.close()
            
        await svc.update_status(payload.run_id, "completed")
    except Exception as e:
        await svc.update_status(payload.run_id, "failed")
        raise e

@asynccontextmanager
async def lifespan(app: FastAPI):
    task_queue.set_handler(_execute_task)
    await task_queue.start()
    yield
    await task_queue.stop()

app = FastAPI(
    title="VeriForm",
    description="Deterministic URL-based form testing platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(runs.router, prefix="/api/v1/runs", tags=["runs"])


@app.get("/api/v1/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}

