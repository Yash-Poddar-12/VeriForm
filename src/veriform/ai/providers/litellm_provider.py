"""
veriform.ai.providers.litellm_provider
======================================
LiteLLM implementation of AI provider.
"""

import asyncio
import time
import json
from typing import Any, Dict, Optional
import litellm

from veriform.ai.providers.base import BaseProvider
from veriform.config import settings
from veriform.utils.logging import get_logger

logger = get_logger(__name__)

class LiteLLMProvider(BaseProvider):
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, response_format: Optional[Any] = None) -> Dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        start_time = time.time()
        
        for attempt in range(settings.ai_max_retries):
            try:
                # Enforce timeout wrapper
                response = await asyncio.wait_for(
                    litellm.acompletion(
                        model=settings.ai_model,
                        messages=messages,
                        temperature=settings.ai_temperature,
                        response_format=response_format
                    ),
                    timeout=settings.ai_timeout_seconds
                )
                
                content = response.choices[0].message.content
                latency = time.time() - start_time
                
                # if response_format is used (json_schema), content should be json string
                parsed = content
                if response_format:
                    try:
                        parsed = json.loads(content)
                    except json.JSONDecodeError:
                        pass
                
                return {
                    "output": parsed,
                    "latency": latency,
                    "model": response.model,
                    "confidence": 0.9 # LiteLLM doesn't expose raw conf, assume high on success
                }
            except (asyncio.TimeoutError, litellm.exceptions.Timeout):
                logger.warning(f"AI Provider timeout (attempt {attempt+1}/{settings.ai_max_retries})")
            except Exception as e:
                logger.warning(f"AI Provider error: {e} (attempt {attempt+1}/{settings.ai_max_retries})")
                
        # Graceful degradation
        return {
            "output": None,
            "latency": time.time() - start_time,
            "error": "Max retries exceeded or timeout."
        }
