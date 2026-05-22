from playwright.async_api import BrowserContext

class TraceRecorder:
    """Wraps Playwright Tracing API to capture zipped evidence for every probe."""
    def __init__(self, context: BrowserContext):
        self.context = context
        
    async def start(self):
        await self.context.tracing.start(screenshots=True, snapshots=True, sources=True)
        
    async def stop(self, output_path: str):
        await self.context.tracing.stop(path=output_path)
