"""
veriform.ai.registry
====================
Provider registry.
"""

from typing import Dict, Type
from veriform.ai.providers.base import BaseProvider
from veriform.ai.providers.litellm_provider import LiteLLMProvider
from veriform.ai.providers.mock_provider import MockProvider
from veriform.config import settings

_registry: Dict[str, Type[BaseProvider]] = {
    "litellm": LiteLLMProvider,
    "mock": MockProvider
}

def get_ai_provider() -> BaseProvider:
    if not settings.enable_ai:
        return MockProvider()
    provider_cls = _registry.get(settings.ai_provider.lower(), MockProvider)
    return provider_cls()
