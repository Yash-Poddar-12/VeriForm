class MutationCandidates:
    """Deterministic boundary candidate generator (Pre-AI phase)."""
    def __init__(self):
        self.boundaries = {
            "email": ["missing_at.com", "@missing_local", "too_long@" + "a"*256 + ".com", "valid@test.com"],
            "pan": ["ABCDE1234", "ABCDE1234FG", "12345ABCDE", "ABCDE1234F"],
            "text": ["", "A", "A" * 1000]
        }
        
    def get_candidates(self, field_type: str) -> list:
        return self.boundaries.get(field_type, ["", "invalid", "valid_text"])
