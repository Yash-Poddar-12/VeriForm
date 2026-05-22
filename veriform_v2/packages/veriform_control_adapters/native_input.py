from veriform_control_adapters.base import ControlAdapter

class NativeTextInputAdapter(ControlAdapter):
    """Adapter for standard <input type='text'> and <textarea>."""
    
    async def fill(self, value: str) -> None:
        async def _do_fill():
            await self.locator.fill(value)
            # Dispatch blur to trigger any blur-based validation handlers
            await self.locator.blur()
        
        await self.retryable_action(_do_fill)
        # NOTE: Callers that need to wait for network side-effects after fill
        # should call sync_manager.wait_for_idle() explicitly.

    async def read_value(self) -> str:
        return await self.locator.input_value()
