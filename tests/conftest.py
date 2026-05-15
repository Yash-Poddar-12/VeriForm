"""
tests/conftest.py
=================
Shared pytest fixtures for the VeriForm test suite.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from veriform.api.app import app


@pytest.fixture()
def sample_run_id() -> str:
    return "run-test-00000000-0000-0000-0000-000000000001"


@pytest.fixture()
async def api_client():
    """Async HTTP client bound to the FastAPI app (no real server required)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client


@pytest.fixture()
def workspace_tmp_path() -> Path:
    """Writable temp directory fixture scoped outside restricted user temp paths."""
    return Path(tempfile.mkdtemp(prefix="veriform-test-", dir="C:\\tmp"))
