import hashlib
from .state import FormState

class EvidenceGenerator:
    """Generates cryptographic hashes combining probe state and delta for replayability."""
    @staticmethod
    def hash_evidence(baseline: FormState, mutated_field: str, value: str, delta) -> str:
        base_str = f"{baseline.hash()}_{mutated_field}_{value}_{delta.hash()}"
        return hashlib.sha256(base_str.encode()).hexdigest()
