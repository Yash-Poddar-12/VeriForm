import asyncio
import os
import sys

# Adjust path to allow imports from packages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from veriform_browser_runtime.manager import BrowserRuntimeManager
from veriform_sync_engine.sync_manager import SyncManager
from veriform_control_adapters.native_input import NativeTextInputAdapter

async def run_benchmark(target_url: str):
    print(f"Starting Hostile Benchmark: {target_url}")
    manager = BrowserRuntimeManager(headless=True)
    await manager.start()
    
    try:
        context = await manager.create_isolated_context()
        page = await context.new_page()
        sync_manager = SyncManager(page)
        
        print("Navigating to target...")
        await page.goto(target_url)
        await sync_manager.setup()
        
        print("Waiting for initial DOM stability...")
        await sync_manager.wait_for_idle()
        
        # Locate hostile input
        email_locator = page.locator("#email")
        adapter = NativeTextInputAdapter(email_locator, sync_manager)
        
        print("Filling hostile input (triggers async trap)...")
        await adapter.fill("test@invalid.com")
        
        print("Checking for validation errors...")
        error_msg = await page.locator("#email-error").text_content()
        print(f"Detected Deterministic Error: {error_msg}")
        
    finally:
        await manager.stop()

if __name__ == "__main__":
    html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../hostile_benchmark_suite/react_async_trap.html"))
    asyncio.run(run_benchmark(f"file://{html_path}"))
