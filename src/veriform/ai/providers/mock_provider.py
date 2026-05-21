"""
veriform.ai.providers.mock_provider
===================================
Deterministic mock provider for testing.
"""

import asyncio
from typing import Any, Dict, Optional
import random

from veriform.ai.providers.base import BaseProvider

class MockProvider(BaseProvider):
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, response_format: Optional[Any] = None) -> Dict[str, Any]:
        await asyncio.sleep(0.01) # small simulated latency
        
        # Mock logic based on keywords
        if "classify" in prompt.lower() or "summary" in prompt.lower():
            output = {"classification": "auth_flow", "confidence": 0.88} if response_format else "auth_flow"
        elif "candidates" in prompt.lower():
            output = {"candidates": ["test@evil.com", "admin' OR 1=1--"]} if response_format else "test@evil.com"
        else:
            output = {"status": "mocked"} if response_format else "mocked response"
            
        return {
            "output": output,
            "latency": 0.01,
            "model": "mock-model-v1",
            "confidence": 1.0
        }
