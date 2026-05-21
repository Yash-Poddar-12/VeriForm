"""Tests for autonomous self-healing capabilities."""

import pytest
from veriform.models.healing import SelectorFingerprint
from veriform.detector.selector_resilience import SelectorResilienceEngine
from veriform.orchestrator.replay_repair import ReplayRepairEngine
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.fixture
def mock_page():
    page = AsyncMock()
    page.evaluate = AsyncMock()
    page.query_selector = AsyncMock()
    return page

@pytest.mark.asyncio
async def test_fingerprint_generation(mock_page):
    element = AsyncMock()
    element.evaluate = AsyncMock(return_value="button")
    element.text_content = AsyncMock(return_value="Submit")
    element.get_attribute = AsyncMock(side_effect=lambda x: "Submit Form" if x == "aria-label" else None)
    element.evaluate.side_effect = ["button", 2] # Mocking tag_name and depth
    
    mock_page.query_selector.return_value = element
    
    engine = SelectorResilienceEngine(mock_page)
    fp = await engine.build_fingerprint("#btn-submit")
    
    assert fp is not None
    assert fp.tag == "button"
    assert fp.text_content == "Submit"
    assert fp.aria_label == "Submit Form"
    assert fp.hierarchy_depth == 2

@pytest.mark.asyncio
async def test_heuristic_scoring(mock_page):
    engine = SelectorResilienceEngine(mock_page)
    
    fp_old = SelectorFingerprint(tag="button", text_content="Next", aria_label="Go Next", hierarchy_depth=3)
    fp_new_exact = SelectorFingerprint(tag="button", text_content="Next", aria_label="Go Next", hierarchy_depth=3)
    fp_new_similar = SelectorFingerprint(tag="button", text_content="Next Step", aria_label="Next", hierarchy_depth=4)
    fp_wrong = SelectorFingerprint(tag="div", text_content="Cancel", hierarchy_depth=1)
    
    score_exact = engine.score_candidate(fp_old, fp_new_exact)
    score_similar = engine.score_candidate(fp_old, fp_new_similar)
    score_wrong = engine.score_candidate(fp_old, fp_wrong)
    
    assert score_exact == 1.0
    assert score_similar > 0.55
    assert score_wrong < 0.55

@pytest.mark.asyncio
async def test_attempt_repair(mock_page):
    engine = SelectorResilienceEngine(mock_page)
    
    # Mock evaluate to return a list of dom element dicts
    mock_page.evaluate.return_value = [
        {"idx": 0, "tag": "div", "text": "Wrong", "aria": "", "placeholder": "", "depth": 1},
        {"idx": 1, "tag": "button", "text": "Submit Form", "aria": "", "placeholder": "", "depth": 2},
    ]
    
    fp_old = SelectorFingerprint(tag="button", text_content="Submit", hierarchy_depth=2)
    
    candidate = await engine.attempt_repair("#broken", fp_old)
    
    assert candidate is not None
    assert candidate.confidence_score > 0.6 # High match due to tag, depth, and partial text match
    assert "button:has-text" in candidate.selector
