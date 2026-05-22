from veriform_core.observation_delta import ObservationDelta
from .confidence_scoring import ConfidenceScorer

class AttributionEngine:
    """Maps deterministic ObservationDeltas back to the specific mutated field."""
    def __init__(self):
        self.scorer = ConfidenceScorer()
        
    def attribute(self, mutated_field: str, delta: ObservationDelta) -> dict:
        import logging
        result = {
            "mutated_field": mutated_field,
            "exact_match": False,
            "solitary_mutation": False,
            "inferred_errors": []
        }
        
        logging.info(f"[Attribution Engine] Analyzing delta for field '{mutated_field}'")
        
        # Attribution Rule 1: Network Failure Match
        for net in delta.network_errors:
            if mutated_field in str(net):
                logging.info(f"[Attribution] Exact Match (Network): {net.get('url')}")
                result["exact_match"] = True
                result["inferred_errors"].append(f"Network 400: {net.get('url')}")
            else:
                logging.info(f"[Attribution] Solitary Match (Network): {net.get('url')}")
                result["solitary_mutation"] = True
                result["inferred_errors"].append(f"Network Rejection: {net.get('url')}")
                
        # Attribution Rule 2: DOM Mutation Match
        for dom in delta.dom_errors:
            if dom.get("target") == mutated_field:
                logging.info(f"[Attribution] Exact Match (DOM): {dom}")
                result["exact_match"] = True
                result["inferred_errors"].append(dom.get("type"))
            elif dom.get("type") == "toast" or dom.get("type") == "aria":
                # Differential Rule: If a generic error appears and we isolated the mutation, it belongs to this field.
                logging.info(f"[Attribution] Solitary Match (DOM): {dom}")
                result["solitary_mutation"] = True
                result["inferred_errors"].append(f"Isolated Error: {dom.get('text') or dom.get('target')}")
                
        result["confidence"] = self.scorer.score(result)
        logging.info(f"[Attribution Engine] Assigned confidence score {result['confidence']} based on signals.")
        return result
