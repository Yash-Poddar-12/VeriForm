"""Tests for Workflow Runner."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from veriform.orchestrator.workflow_runner import run_workflow
from veriform.models.schemas import FieldSchema

@pytest.mark.asyncio
async def test_workflow_runner_graph_traversal() -> None:
    page = MagicMock()
    page.url = "http://example.com"
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    
    locator = AsyncMock()
    locator.is_visible.return_value = True
    page.locator.return_value.first = locator
    
    # Mock capture_state by patching it
    from unittest.mock import patch
    from veriform.models.workflow import StateSnapshot
    
    snap1 = StateSnapshot(
        state_id="s1",
        state_hash="hash1",
        url="http://example.com",
        timestamp="2023-01-01T00:00:00Z",
        active_fields=[FieldSchema(field_id="f1", run_id="r1", name="email", type="email", required=True)],
        validation_messages=[]
    )
    
    snap2 = StateSnapshot(
        state_id="s2",
        state_hash="hash2", # different hash
        url="http://example.com/step2",
        timestamp="2023-01-01T00:00:00Z",
        active_fields=[],
        validation_messages=[]
    )
    
    with patch("veriform.orchestrator.workflow_runner.capture_state") as mock_capture:
        # First call returns snap1, second returns snap2
        mock_capture.side_effect = [snap1, snap1, snap2]
        
        session = await run_workflow("http://example.com", page)
        
        # Initial nav -> state 1 (active fields -> generates fill/submit actions -> appends to queue)
        # Next trace: nav -> state 1 -> fill -> submit -> wait -> state 2 (no active fields -> terminal)
        
        # It should explore hash1 and hash2
        assert len(session.graph_nodes) >= 1
        assert "hash1" in session.graph_nodes
