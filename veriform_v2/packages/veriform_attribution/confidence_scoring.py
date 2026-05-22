class ConfidenceScorer:
    """Assigns deterministic confidence scores to validation attributions."""
    @staticmethod
    def score(attribution: dict) -> float:
        if attribution.get("exact_match"): return 1.0 # High confidence: ID matched
        if attribution.get("solitary_mutation"): return 0.7 # Medium confidence: Only field changed
        return 0.0
