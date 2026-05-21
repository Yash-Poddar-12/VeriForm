"""Tests for ActionEngine."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from veriform.models.workflow import ActionSchema
from veriform.executor.action_engine import ActionEngine

@pytest.mark.asyncio
async def test_action_engine_fill() -> None:
    page = MagicMock()
    locator = AsyncMock()
    page.locator.return_value.first = locator
    
    engine = ActionEngine(page)
    action = ActionSchema(
        action_id="a1",
        type="fill",
        selector="#email",
        value="test@example.com"
    )
    
    await engine.execute_action(action)
    
    page.locator.assert_called_with("#email")
    locator.fill.assert_called_with("test@example.com", timeout=5000)

@pytest.mark.asyncio
async def test_action_engine_click() -> None:
    page = MagicMock()
    locator = AsyncMock()
    page.locator.return_value.first = locator
    
    engine = ActionEngine(page)
    action = ActionSchema(
        action_id="a2",
        type="click",
        selector="#btn"
    )
    
    await engine.execute_action(action)
    
    page.locator.assert_called_with("#btn")
    locator.click.assert_called_with(timeout=5000)
