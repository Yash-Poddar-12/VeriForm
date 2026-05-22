import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from veriform_browser_runtime.manager import BrowserRuntimeManager
from veriform_sync_engine.sync_manager import SyncManager
from veriform_replay.replay_serializer import ReplaySerializer
from veriform_replay.playwright_generator import PlaywrightScriptGenerator
from veriform_evidence.evidence_collector import EvidenceCollector

async def run_evidence_harness(target_url: str):
    print(f"Starting Evidence Harness on: {target_url}")
    manager = BrowserRuntimeManager(headless=True)
    await manager.start()
    
    try:
        context = await manager.create_isolated_context()
        page = await context.new_page()
        sync_manager = SyncManager(page)
        
        collector = EvidenceCollector(context, page)
        serializer = ReplaySerializer()
        
        # Start Trace
        await collector.start_probe()
        
        print("Navigating...")
        await page.goto(target_url)
        serializer.record_goto(target_url)
        await sync_manager.setup()
        
        print("Filling invalid data...")
        await page.locator("#pan").fill("123")
        serializer.record_fill("#pan", "123")
        
        print("Submitting...")
        await page.locator("#btn").click()
        serializer.record_click("#btn")
        
        await sync_manager.wait_for_idle()
        
        # Stop Trace & Hash
        output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../output"))
        trace_path, final_hash = await collector.end_probe("probe_pan_123", output_dir)
        print(f"\\nEvidence Trace saved to: {trace_path}")
        print(f"Cryptographic Trace Hash: {final_hash}")
        
        # Generate Playwright Replay Script
        replay_json = serializer.to_json()
        script_path = os.path.join(output_dir, "replay_pan_123.py")
        PlaywrightScriptGenerator.generate(replay_json, script_path)
        print(f"Playwright Replay Script generated: {script_path}")
        
    finally:
        await manager.stop()

if __name__ == "__main__":
    html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../hostile_benchmark_suite/aria_hidden_validation.html"))
    asyncio.run(run_evidence_harness(f"file://{html_path}"))
