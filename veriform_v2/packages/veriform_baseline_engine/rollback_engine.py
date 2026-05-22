from playwright.async_api import Page
from veriform_core.state import FormState
from veriform_sync_engine.sync_manager import SyncManager
from veriform_control_adapters.native_input import NativeTextInputAdapter

class RollbackEngine:
    """Implements strict isolation by reloading page instead of undoing UI."""
    def __init__(self, page: Page, sync_manager: SyncManager):
        self.page = page
        self.sync_manager = sync_manager
        
    async def restore_baseline(self, state: FormState):
        await self.page.reload()
        await self.sync_manager.setup()
        await self.sync_manager.wait_for_idle()
        
        for field_id, value in state.values.items():
            locator = self.page.locator(f"#{field_id}")
            if await locator.count() == 0:
                locator = self.page.locator(f"[name='{field_id}']")
                
            if await locator.count() > 0:
                adapter = NativeTextInputAdapter(locator.first, self.sync_manager)
                await adapter.fill(value)
