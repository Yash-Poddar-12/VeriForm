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

async def async_main():
    manager = BrowserRuntimeManager(headless=True)
    await manager.start()
    try:
        context = await manager.create_isolated_context()
        page = await context.new_page()
        sync_manager = SyncManager(page)
        target_url = "file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "hostile_benchmark_suite", "optimistic_ui.html"))
        await page.goto(target_url)
        await sync_manager.setup()
        
        baseline = FormState(url=target_url, values={"pan": "ABCDE1234F"})
        rollback = RollbackEngine(page, sync_manager)
        executor = ProbeExecutor(page, sync_manager, rollback)
        observer = ValidationObserver(page)
        mutator = DifferentialMutator(executor, sync_manager, observer)
        
        results = await mutator.test_field(baseline, "pan", "pan")
        for r in results:
            print(f"Mutated PAN -> {r.candidate_value} | Errors: {r.attribution.get('inferred_errors')}")
    finally:
        await manager.stop()

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
