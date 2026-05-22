import asyncio
import os
import sys

# Adjust path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from veriform_browser_runtime.manager import BrowserRuntimeManager
from veriform_sync_engine.sync_manager import SyncManager
from veriform_baseline_engine.baseline_engine import BaselineEngine

async def run_baseline_discovery(target_url: str):
    print(f"Starting Baseline Discovery on: {target_url}")
    manager = BrowserRuntimeManager(headless=True)
    await manager.start()
    
    try:
        context = await manager.create_isolated_context()
        page = await context.new_page()
        sync_manager = SyncManager(page)
        
        engine = BaselineEngine(page, sync_manager)
        
        try:
            valid_state = await engine.discover_baseline(target_url)
            print(f"\nFinal Valid Baseline Discovered:\n{valid_state.values}")
        except Exception as e:
            print(f"Baseline Discovery Failed: {e}")
        
    finally:
        await manager.stop()

if __name__ == "__main__":
    html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../hostile_benchmark_suite/generic_toast.html"))
    asyncio.run(run_baseline_discovery(f"file://{html_path}"))
