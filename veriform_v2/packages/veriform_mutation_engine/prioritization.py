class PrioritizationEngine:
    """Sorts candidates to test edge cases first deterministically."""
    def prioritize(self, candidates: list) -> list:
        def score(c):
            if c == "": return 0
            if len(str(c)) > 100: return 1
            return 2
        return sorted(candidates, key=lambda c: (score(c), str(c)))
