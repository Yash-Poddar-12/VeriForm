"""
Final targeted diagnostic: runs the EXACT same code path as probe_executor
but with verbose response capture to identify where the lambda fails.
"""
import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath("packages"))

from veriform_browser_runtime.manager import BrowserRuntimeManager
from veriform_sync_engine.sync_manager import SyncManager

async def diagnose():
    manager = BrowserRuntimeManager(headless=True)
    await manager.start()
    context = await manager.create_isolated_context()
    page = await context.new_page()
    sync_manager = SyncManager(page)

    # Exact same order as probe_executor
    await page.reload(wait_until="domcontentloaded")
    await sync_manager.setup()

    # Wait for first navigate separately
    await page.goto("http://127.0.0.1:8000/optimistic_ui.html", wait_until="domcontentloaded")

    print(f"failed_responses after goto: {sync_manager.failed_responses}")

    # Fill invalid PAN  
    await page.locator("#pan").fill("ABCDE1234")

    # Reset and submit
    sync_manager.reset_probe_state()
    print(f"After reset: {sync_manager.failed_responses}")

    await page.locator("#btn").click()
    print("Clicked. Waiting 2000ms for setTimeout...")
    await page.wait_for_timeout(2000)
    print(f"After wait_for_timeout: {sync_manager.failed_responses}")

    await page.wait_for_load_state("networkidle")
    print(f"After networkidle: {sync_manager.failed_responses}")

    # Also manually trigger the fetch to see if listener works at all
    print("\nManually triggering fetch via page.evaluate...")
    sync_manager.reset_probe_state()
    await page.evaluate("() => fetch('/trigger_400')")
    await page.wait_for_timeout(2000)
    print(f"After manual fetch: {sync_manager.failed_responses}")

    await manager.stop()

asyncio.run(diagnose())
