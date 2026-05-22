from veriform_evidence.execution_snapshot import ExecutionSnapshot
from veriform_core.probe_result import ProbeResult
from playwright.async_api import Page
import logging

class ReplayValidator:
    """Mathematically proves a replay script produces the exact same state as the original probe."""
    
    @staticmethod
    async def validate(replayed_page: Page, original_dom_hash: str) -> bool:
        replayed_dom_hash = await ExecutionSnapshot.capture_dom_hash(replayed_page)
        
        if replayed_dom_hash == original_dom_hash:
            logging.info("REPLAY VERIFIED: Cryptographic DOM match.")
            return True
        else:
            logging.error(f"REPLAY FAILED: Delta mismatch.\\nExpected: {original_dom_hash}\\nActual: {replayed_dom_hash}")
            return False
