import hashlib

class HashChain:
    """Cryptographically links events to guarantee deterministic execution lineage."""
    def __init__(self, initial_seed: str):
        self.current_hash = hashlib.sha256(initial_seed.encode()).hexdigest()
        self.chain = [self.current_hash]
        
    def link(self, payload: str) -> str:
        """Appends a new event payload to the chain."""
        combined = self.current_hash + payload
        self.current_hash = hashlib.sha256(combined.encode()).hexdigest()
        self.chain.append(self.current_hash)
        return self.current_hash
