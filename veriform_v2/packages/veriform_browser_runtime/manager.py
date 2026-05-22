from playwright.async_api import async_playwright, Browser, BrowserContext

class BrowserRuntimeManager:
    """Manages the lifecycle of the Playwright browser and isolated contexts."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self.browser: Browser = None

    async def start(self):
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(headless=self.headless)

    async def create_isolated_context(self) -> BrowserContext:
        """Creates a purely isolated incognito context for deterministic probe execution."""
        if not self.browser:
            raise RuntimeError("Browser not started")
        return await self.browser.new_context(
            ignore_https_errors=True,
            bypass_csp=True
        )

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
