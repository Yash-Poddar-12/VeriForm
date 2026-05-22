from playwright.async_api import Page
from veriform_core.state import FormState
from veriform_sync_engine.sync_manager import SyncManager
from veriform_baseline_engine.rollback_engine import RollbackEngine
import logging


class ProbeExecutor:
    """
    Executes a single mutation probe using deterministic rollback and raw Playwright fills.

    Key design constraints:
    - Uses page.reload(wait_until="networkidle") to guarantee the page is fully quiesced
      before filling fields. This prevents false-positive networkidle states.
    - Waits page.wait_for_timeout(800) after click to allow JS setTimeout(500ms) deferred
      fetches to fire before reading failed_responses.
    - Does NOT use wait_for_load_state("networkidle") after click — that state may already
      be cached from the reload and returns immediately, missing deferred fetches.
    """
    def __init__(self, page: Page, sync_manager: SyncManager, rollback: RollbackEngine):
        self.page = page
        self.sync_manager = sync_manager
        self.rollback = rollback

    async def execute(self, baseline: FormState, mutated_field: str, candidate: str):
        # 1. Hard reload — wait until networkidle so page is fully quiesced
        #    (prevents false-positive networkidle reads after the button click)
        await self.page.reload(wait_until="networkidle")
        # Re-attach response listener on the new document
        await self.sync_manager.setup()

        # 2. Fast-forward baseline values (raw fill, no blur, no wait)
        for field_id, value in baseline.values.items():
            if field_id == mutated_field:
                continue
            loc = self.page.locator(f"#{field_id}")
            if await loc.count() == 0:
                loc = self.page.locator(f"[name='{field_id}']")
            if await loc.count() > 0:
                await loc.fill(value)

        # 3. Mutate exactly one field
        mut_loc = self.page.locator(f"#{mutated_field}")
        if await mut_loc.count() == 0:
            mut_loc = self.page.locator(f"[name='{mutated_field}']")
        if await mut_loc.count() > 0:
            await mut_loc.fill(candidate)
            logging.info(f"[ProbeExecutor] Filled '{mutated_field}' = '{candidate}'")

        # 4. Open clean observation window
        self.sync_manager.reset_probe_state()

        # 5. Submit form
        submit_btn = self.page.locator("button[type='submit'], input[type='submit']")
        count = await submit_btn.count()
        logging.info(f"[ProbeExecutor] Submit button count: {count}")
        if count > 0:
            await submit_btn.first.click()
            logging.info("[ProbeExecutor] Clicked. Waiting 2000ms for JS timers + network...")
            # Wait long enough for any JS-deferred fetch (setTimeout 500ms + server latency 500ms)
            await self.page.wait_for_timeout(2000)
            logging.info(f"[ProbeExecutor] Post-wait failed_responses: {self.sync_manager.failed_responses}")
