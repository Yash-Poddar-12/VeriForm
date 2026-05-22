"""
Targeted diagnostic: verifies whether SyncManager response lambda captures
failed_responses correctly when page.reload() happens inside the same context.
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

    await sync_manager.setup()

    print(f"SyncManager id: {id(sync_manager)}")
    print(f"failed_responses list id: {id(sync_manager.failed_responses)}")

    await page.goto("http://127.0.0.1:8000/optimistic_ui.html")
    await page.wait_for_load_state("domcontentloaded")

    # Fill invalid PAN
    await page.locator("#pan").fill("ABCDE1234")

    # Reset probe state, then submit
    sync_manager.reset_probe_state()
    print(f"After reset, failed_responses: {sync_manager.failed_responses}")

    await page.locator("#btn").click()
    print("Clicked. Waiting 2000ms...")
    await page.wait_for_timeout(2000)
    await page.wait_for_load_state("networkidle")

    print(f"\nfailed_responses after wait: {sync_manager.failed_responses}")
    print(f"failed_responses list id after wait: {id(sync_manager.failed_responses)}")

    await manager.stop()

asyncio.run(diagnose())
