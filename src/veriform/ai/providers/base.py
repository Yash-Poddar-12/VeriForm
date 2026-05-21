"""
veriform.ai.providers.base
==========================
Base interface for AI providers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseProvider(ABC):
    """Abstract interface for AI generation."""
    
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, response_format: Optional[Any] = None) -> Dict[str, Any]:
        """Generate response with timeout and retry bounds."""
        pass
