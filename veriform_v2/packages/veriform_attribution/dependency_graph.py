class DependencyGraph:
    """Tracks field dependencies dynamically based on observed side-effects."""
    def __init__(self):
        self.edges = {}
        
    def add_edge(self, mutated_field: str, affected_field: str):
        if mutated_field not in self.edges:
            self.edges[mutated_field] = set()
        self.edges[mutated_field].add(affected_field)
