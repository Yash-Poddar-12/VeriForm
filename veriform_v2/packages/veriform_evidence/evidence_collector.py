from veriform_evidence.trace_recorder import TraceRecorder
from veriform_evidence.execution_snapshot import ExecutionSnapshot
from veriform_evidence.hash_chain import HashChain
from playwright.async_api import BrowserContext, Page
import os

class EvidenceCollector:
    """Gathers all traces, network events, and DOM states for a probe."""
    def __init__(self, context: BrowserContext, page: Page):
        self.trace_recorder = TraceRecorder(context)
        self.page = page
        self.chain = HashChain("session_seed")
        
    async def start_probe(self):
        await self.trace_recorder.start()
        
    async def end_probe(self, probe_id: str, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)
        trace_path = os.path.join(output_dir, f"trace_{probe_id}.zip")
        await self.trace_recorder.stop(trace_path)
        
        dom_hash = await ExecutionSnapshot.capture_dom_hash(self.page)
        final_hash = self.chain.link(dom_hash)
        return trace_path, final_hash
