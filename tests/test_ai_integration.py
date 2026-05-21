"""Tests for AI integration, Semantic Clustering, and Visual Analysis."""

import pytest
from pathlib import Path
from veriform.ai.registry import get_ai_provider
from veriform.ai.providers.mock_provider import MockProvider
from veriform.detector.state_summarizer import StateSummarizer
from veriform.analyzer.visual_analysis import VisualAnalysisPipeline
from veriform.models.schemas import FieldSchema

@pytest.mark.asyncio
async def test_mock_provider_deterministic():
    provider = MockProvider(seed=123)
    res = await provider.generate("Give me candidates for email", response_format={"type": "json_object"})
    
    assert res["latency"] > 0
    assert "candidates" in res["output"]
    assert "test@evil.com" in res["output"]["candidates"]

@pytest.mark.asyncio
async def test_semantic_state_summarizer():
    summarizer = StateSummarizer()
    fields = [FieldSchema(field_id="1", run_id="r", type="email", name="email", dom_id="email", required=True)]
    
    state = await summarizer.summarize_state("hash_auth", fields, "Login Portal")
    assert state.classification == "auth_flow"
    assert state.confidence == 0.8
    assert state.raw_hash == "hash_auth"
    
    state2 = await summarizer.summarize_state("hash_pay", fields, "Checkout and Billing")
    assert state2.classification == "payment_flow"
    
@pytest.mark.asyncio
async def test_visual_analysis_missing_image(tmp_path):
    pipeline = VisualAnalysisPipeline()
    res = pipeline.compute_visual_drift(tmp_path / "a.png", tmp_path / "b.png")
    assert "error" in res

# Note: VisualAnalysis tests with real images would go here, 
# but we mock it or skip it in CI if images aren't present.
