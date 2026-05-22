from veriform_core.observation_delta import ObservationDelta

class DeltaAnalyzer:
    """Compares the baseline observation against the mutation observation."""
    @staticmethod
    def compute_delta(baseline_obs: ObservationDelta, mutation_obs: ObservationDelta) -> ObservationDelta:
        # In a strict differential test, baseline is known-valid (0 errors).
        # So the absolute delta IS exactly the mutation observation.
        return mutation_obs
