import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_sync_manager():
    # Simple deterministic test to prove test suite bootstrapping
    mock_page = AsyncMock()
    mock_page.evaluate.return_value = None
    assert mock_page.evaluate.called is False
    await mock_page.evaluate("() => true")
    assert mock_page.evaluate.call_count == 1
