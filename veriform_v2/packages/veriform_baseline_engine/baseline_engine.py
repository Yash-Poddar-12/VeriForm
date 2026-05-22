from veriform_core.state import FormState
from veriform_browser_runtime.form_discovery import FormDiscovery
from veriform_browser_runtime.validation_observer import ValidationObserver
from veriform_baseline_engine.candidate_generator import CandidateGenerator
from veriform_baseline_engine.rollback_engine import RollbackEngine
from veriform_baseline_engine.convergence import ConvergenceTracker
from veriform_core.budget import ProbeBudget
from veriform_sync_engine.sync_manager import SyncManager
from playwright.async_api import Page
import logging

logging.basicConfig(level=logging.INFO)

class BaselineEngine:
    """The core engine orchestrating baseline discovery via iterative generation."""
    def __init__(self, page: Page, sync_manager: SyncManager):
        self.page = page
        self.sync_manager = sync_manager
        self.discovery = FormDiscovery(page)
        self.observer = ValidationObserver(page)
        self.generator = CandidateGenerator()
        self.rollback = RollbackEngine(page, sync_manager)
        self.budget = ProbeBudget()
        self.convergence = ConvergenceTracker(self.budget)
        
    async def discover_baseline(self, url: str) -> FormState:
        await self.page.goto(url)
        await self.sync_manager.setup()
        await self.sync_manager.wait_for_idle()
        
        fields = await self.discovery.discover_fields()
        state = FormState(url=url)
        
        for field in fields:
            field_id = field.get('id') or field.get('name')
            if not field_id: continue
            f_type = self.generator.guess_type(field)
            state = state.set(field_id, self.generator.generate_candidate(f_type, 0))
            
        attempts = 0
        while attempts < self.budget.max_form_attempts:
            attempts += 1
            logging.info(f"Baseline Attempt {attempts}: {state.values}")
            
            await self.rollback.restore_baseline(state)
            
            # Submit generic button
            submit_btn = self.page.locator("button[type='submit'], input[type='submit']")
            if await submit_btn.count() > 0:
                await submit_btn.first.click()
            
            await self.sync_manager.wait_for_idle()
            
            # Since requests aren't attached with responses in the basic sync_manager, pass []
            # Or assume any visible generic error means validation failed.
            delta = await self.observer.observe_delta(None, [])
            logging.info(f"Observation Delta: {delta}")
            
            self.convergence.record_delta(delta)
            if self.convergence.check_stagnation():
                raise RuntimeError("Stagnation: Same error repeated 3 times.")
                
            if not delta["dom_errors"] and not delta["network_errors"]:
                logging.info(f"SUCCESS: Valid baseline discovered: {state.values}")
                return state
                
            # Mutate fields that had errors (or all if generic)
            # Increment attempt index for candidate generation
            for field in fields:
                field_id = field.get('id') or field.get('name')
                if not field_id: continue
                f_type = self.generator.guess_type(field)
                state = state.set(field_id, self.generator.generate_candidate(f_type, attempts))
            
        raise RuntimeError("Budget exhausted before discovering baseline")
