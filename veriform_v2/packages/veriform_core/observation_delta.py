from pydantic import BaseModel, Field
from typing import List, Dict
import hashlib
import json

class ObservationDelta(BaseModel):
    """Deterministic snapshot of DOM and Network failures."""
    dom_errors: List[Dict] = Field(default_factory=list)
    network_errors: List[Dict] = Field(default_factory=list)
    
    def hash(self) -> str:
        serialized = json.dumps({
            "dom": sorted([str(e) for e in self.dom_errors]),
            "net": sorted([str(e) for e in self.network_errors])
        })
        return hashlib.sha256(serialized.encode()).hexdigest()
        
    def is_empty(self) -> bool:
        return len(self.dom_errors) == 0 and len(self.network_errors) == 0
