from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from datetime import datetime

class ObservationEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str
    payload: Dict[str, Any]

class DOMMutationEvent(ObservationEvent):
    event_type: str = "DOM_MUTATION"
    target_selector: str
    mutation_type: str

class NetworkEvent(ObservationEvent):
    event_type: str = "NETWORK_REQUEST"
    url: str
    method: str
    status: Optional[int] = None
