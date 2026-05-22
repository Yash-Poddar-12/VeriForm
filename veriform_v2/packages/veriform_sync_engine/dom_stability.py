import asyncio
from playwright.async_api import Page
import time

class DOMStabilityDetector:
    """Injects observers to track DOM mutations deterministically."""
    
    def __init__(self, page: Page, debounce_ms: int = 500):
        self.page = page
        self.debounce_ms = debounce_ms
        self._is_injected = False

    async def inject_observer(self):
        script = """
        () => {
            if (window.__vf_observer) return;
            window.__vf_last_mutation = Date.now();
            window.__vf_observer = new MutationObserver((mutations) => {
                window.__vf_last_mutation = Date.now();
            });
            window.__vf_observer.observe(document.body, { 
                childList: true, subtree: true, attributes: true, characterData: true 
            });
        }
        """
        await self.page.evaluate(script)
        self._is_injected = True

    async def wait_for_stability(self, timeout_ms: int = 10000):
        """Sleep-free polling for DOM stability based on MutationObserver timestamps."""
        if not self._is_injected:
            raise RuntimeError("DOM observer not injected. Call inject_observer() first.")
            
        start_time = time.time()
        while (time.time() - start_time) * 1000 < timeout_ms:
            last_mutation = await self.page.evaluate("window.__vf_last_mutation || 0")
            now = await self.page.evaluate("Date.now()")
            
            if (now - last_mutation) > self.debounce_ms:
                return True
                
            await asyncio.sleep(0.05) # Yield to event loop
            
        raise TimeoutError(f"DOM did not stabilize within {timeout_ms}ms")
