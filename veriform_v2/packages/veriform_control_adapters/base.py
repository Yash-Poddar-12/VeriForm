import asyncio
from abc import ABC, abstractmethod
from playwright.async_api import Locator, Error as PlaywrightError
from veriform_sync_engine.sync_manager import SyncManager
from typing import Callable, Awaitable

class ControlAdapter(ABC):
    """Base class for all UI component interactions, isolating framework quirks."""
    
    def __init__(self, locator: Locator, sync_manager: SyncManager):
        self.locator = locator
        self.sync_manager = sync_manager

    @abstractmethod
    async def fill(self, value: str) -> None:
        pass

    @abstractmethod
    async def read_value(self) -> str:
        pass

    async def retryable_action(self, action: Callable[[], Awaitable[None]], max_retries: int = 3):
        """Core anti-flake primitive. Recovers from StaleElementReference errors."""
        for attempt in range(max_retries):
            try:
                await action()
                return
            except PlaywrightError as e:
                # Playwright raises specific errors when elements detach from DOM
                if "stale" in str(e).lower() or "detached" in str(e).lower():
                    if attempt == max_retries - 1:
                        raise e
                    # Yield and wait for DOM to stabilize before retrying
                    await self.sync_manager.wait_for_idle()
                else:
                    raise e
