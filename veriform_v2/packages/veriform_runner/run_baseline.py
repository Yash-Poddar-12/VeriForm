import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from veriform_browser_runtime.manager import BrowserRuntimeManager
from veriform_sync_engine.sync_manager import SyncManager
from veriform_baseline_engine.baseline_engine import BaselineEngine

async def async_main():
    manager = BrowserRuntimeManager(headless=True)
    await manager.start()
    try:
        context = await manager.create_isolated_context()
        page = await context.new_page()
        sync_manager = SyncManager(page)
        engine = BaselineEngine(page, sync_manager)
        target_url = "file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "hostile_benchmark_suite", "generic_toast.html"))
        state = await engine.discover_baseline(target_url)
        print(f"Discovered baseline: {state.values}")
    finally:
        await manager.stop()

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
