import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from veriform_browser_runtime.manager import BrowserRuntimeManager
from veriform_sync_engine.sync_manager import SyncManager
from veriform_baseline_engine.rollback_engine import RollbackEngine
from veriform_browser_runtime.validation_observer import ValidationObserver
from veriform_mutation_engine.probe_executor import ProbeExecutor
from veriform_mutation_engine.differential_mutator import DifferentialMutator
from veriform_core.state import FormState

# Benchmark server runs at http://127.0.0.1:8000
# HTML files are served at the root: http://127.0.0.1:8000/<filename>.html
# /trigger_400 is served at: http://127.0.0.1:8000/trigger_400
TARGET_URL = "http://127.0.0.1:8000/optimistic_ui.html"

async def run_mutation_test(target_url: str):
    print(f"Starting Differential Mutation Harness on: {target_url}")
    manager = BrowserRuntimeManager(headless=True)
    await manager.start()
    
    try:
        context = await manager.create_isolated_context()
        page = await context.new_page()
        sync_manager = SyncManager(page)

        # Setup BEFORE page.goto so listeners are attached before any navigation
        await sync_manager.setup()
        await page.goto(target_url)
        
        # Simulated valid baseline: a 10-char PAN is the valid state on this trap
        baseline = FormState(url=target_url, values={"pan": "ABCDE1234F"})
        
        rollback = RollbackEngine(page, sync_manager)
        executor = ProbeExecutor(page, sync_manager, rollback)
        observer = ValidationObserver(page)
        mutator = DifferentialMutator(executor, sync_manager, observer)
        
        print(f"\n[DIAG] sync_manager id: {id(sync_manager)}")
        print(f"[DIAG] executor.sync_manager id: {id(executor.sync_manager)}")
        print(f"[DIAG] failed_responses list id: {id(sync_manager.failed_responses)}")
        
        # Test with invalid PAN values — all shorter than 10 chars trigger the fetch
        results = await mutator.test_field(baseline, "pan", "pan")
        
        print("\n=== FINAL MUTATION ATTRIBUTIONS ===")
        for r in results:
            status = "CONFIRMED_REJECTED" if r.confidence_score > 0 else "UNKNOWN"
            print(f"Candidate: '{r.candidate_value}' -> {status} | Score: {r.confidence_score} | Errors: {r.attribution['inferred_errors']}")
            
    finally:
        await manager.stop()

if __name__ == "__main__":
    asyncio.run(run_mutation_test(TARGET_URL))
