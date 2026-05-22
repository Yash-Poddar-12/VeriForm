import json
from typing import List, Dict

class ReplaySerializer:
    """Serializes deterministic browser actions into a JSON sequence."""
    def __init__(self):
        self.sequence: List[Dict] = []
        
    def record_goto(self, url: str):
        self.sequence.append({"action": "goto", "url": url})
        
    def record_fill(self, selector: str, value: str):
        self.sequence.append({"action": "fill", "selector": selector, "value": value})
        
    def record_click(self, selector: str):
        self.sequence.append({"action": "click", "selector": selector})
        
    def to_json(self) -> str:
        return json.dumps(self.sequence, indent=2)
