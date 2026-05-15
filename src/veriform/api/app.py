"""
veriform.api.app
=================
FastAPI application factory and route registration.

Start the server:
    uvicorn veriform.api.app:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI

from veriform.api.routes import runs

app = FastAPI(
    title="VeriForm",
    description="Deterministic URL-based form testing platform",
    version="0.1.0",
)

app.include_router(runs.router, prefix="/runs", tags=["runs"])


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}
