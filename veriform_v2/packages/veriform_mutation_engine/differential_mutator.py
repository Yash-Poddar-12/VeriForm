from veriform_core.state import FormState
from veriform_core.observation_delta import ObservationDelta
from veriform_core.probe_result import ProbeResult
from veriform_core.evidence import EvidenceGenerator
from .probe_executor import ProbeExecutor
from .mutation_candidates import MutationCandidates
from .prioritization import PrioritizationEngine
from veriform_attribution.attribution_engine import AttributionEngine
from veriform_browser_runtime.validation_observer import ValidationObserver
from veriform_sync_engine.sync_manager import SyncManager
import logging

logging.basicConfig(level=logging.INFO)

class DifferentialMutator:
    """The core engine orchestrating isolation-based mutation testing."""
    def __init__(self, executor: ProbeExecutor, sync_manager: SyncManager, observer: ValidationObserver):
        self.executor = executor
        self.sync_manager = sync_manager
        self.observer = observer
        self.candidates = MutationCandidates()
        self.prioritizer = PrioritizationEngine()
        self.attributor = AttributionEngine()
        
    async def test_field(self, baseline: FormState, field_id: str, field_type: str) -> list[ProbeResult]:
        logging.info(f"Starting Differential Mutation for field: {field_id}")
        results = []
        raw_candidates = self.candidates.get_candidates(field_type)
        prioritized = self.prioritizer.prioritize(raw_candidates)
        
        for candidate in prioritized:
            logging.info(f"Testing Candidate: {candidate}")
            
            await self.executor.execute(baseline, field_id, candidate)
            
            # Observe network & DOM
            failed_requests = self.sync_manager.failed_responses
            logging.info(f"[Delta Capture] sync_manager id: {id(self.sync_manager)} | failed_responses id: {id(self.sync_manager.failed_responses)}")
            logging.info(f"[Delta Capture] Extracted {len(failed_requests)} network failures from SyncManager.")
            raw_delta = await self.observer.observe_delta(None, failed_requests)
            logging.info(f"[Delta Capture] DOM Observer extracted: {raw_delta['dom_errors']}")
            delta = ObservationDelta(dom_errors=raw_delta["dom_errors"], network_errors=raw_delta["network_errors"])
            
            # Attribute differential causality
            attribution = self.attributor.attribute(field_id, delta)
            
            # Hash evidence for replay verification
            ev_hash = EvidenceGenerator.hash_evidence(baseline, field_id, candidate, delta)
            
            result = ProbeResult(
                mutated_field=field_id,
                candidate_value=candidate,
                baseline_hash=baseline.hash(),
                delta=delta,
                attribution=attribution,
                confidence_score=attribution["confidence"],
                evidence_hash=ev_hash
            )
            results.append(result)
            logging.info(f"Result Hash: {ev_hash} | Confidence: {result.confidence_score}")
            
        return results
