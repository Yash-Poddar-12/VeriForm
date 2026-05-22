import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from veriform_browser_runtime.manager import BrowserRuntimeManager
from veriform_sync_engine.sync_manager import SyncManager
from veriform_baseline_engine.baseline_engine import BaselineEngine
from veriform_mutation_engine.probe_executor import ProbeExecutor
from veriform_mutation_engine.differential_mutator import DifferentialMutator
from veriform_browser_runtime.validation_observer import ValidationObserver
from veriform_evidence.evidence_collector import EvidenceCollector
from veriform_replay.replay_serializer import ReplaySerializer
from veriform_replay.playwright_generator import PlaywrightScriptGenerator
from veriform_reporting.json_reporter import JsonReporter
from veriform_reporting.html_reporter import HtmlReporter

async def async_main():
    print("Starting End-to-End VeriForm Benchmark Execution...")
    manager = BrowserRuntimeManager(headless=True)
    await manager.start()
    
    try:
        context = await manager.create_isolated_context()
        page = await context.new_page()
        sync_manager = SyncManager(page)
        
        target_url = "file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "hostile_benchmark_suite", "optimistic_ui.html"))
        
        print("1. Baseline Discovery")
        engine = BaselineEngine(page, sync_manager)
        baseline = await engine.discover_baseline(target_url)
        print(f"Baseline Discovered: {baseline.values}")
        
        print("2. Mutation & Evidence Collection")
        collector = EvidenceCollector(context, page)
        serializer = ReplaySerializer()
        
        await collector.start_probe()
        await page.goto(target_url)
        serializer.record_goto(target_url)
        await sync_manager.setup()
        
        from veriform_baseline_engine.rollback_engine import RollbackEngine
        rollback = RollbackEngine(page, sync_manager)
        executor = ProbeExecutor(page, sync_manager, rollback)
        observer = ValidationObserver(page)
        mutator = DifferentialMutator(executor, sync_manager, observer)
        
        results = await mutator.test_field(baseline, "pan", "pan")
        
        output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "output"))
        os.makedirs(output_dir, exist_ok=True)
        
        trace_path, final_hash = await collector.end_probe("end_to_end_probe", output_dir)
        print(f"Evidence Trace Hash: {final_hash}")
        
        print("3. Generating Reports")
        JsonReporter.export(results, os.path.join(output_dir, "report.json"))
        HtmlReporter.generate(results, os.path.join(output_dir, "report.html"))
        
        print("4. Replay Artifact Generation")
        script_path = os.path.join(output_dir, "replay.py")
        PlaywrightScriptGenerator.generate(serializer.to_json(), script_path)
        print("End-to-End Execution Complete. Output available in /output directory.")
        
    finally:
        await manager.stop()

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
