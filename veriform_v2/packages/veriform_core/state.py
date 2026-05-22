import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass(frozen=True)
class FormState:
    url: str
    values: Dict[str, Any] = field(default_factory=dict)
    
    def hash(self) -> str:
        serialized = json.dumps({"url": self.url, "values": self.values}, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()
        
    def clone(self) -> 'FormState':
        return FormState(url=self.url, values=dict(self.values))
        
    def set(self, field_id: str, value: Any) -> 'FormState':
        new_values = dict(self.values)
        new_values[field_id] = value
        return FormState(url=self.url, values=new_values)
