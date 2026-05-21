"""
veriform.models.workflow
========================
Data structures for the Stateful Form Workflow Engine.
These models represent the execution context, state snapshots, and traversal graphs
for multi-step, dynamic form workflows.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from veriform.models.schemas import FieldSchema, ResultSchema

ActionType = Literal["fill", "click", "select", "wait", "navigate", "submit"]

class ActionSchema(BaseModel):
    """A discrete interaction performed by the executor on the DOM."""

    action_id: str = Field(..., description="Unique ID for this action")
    type: ActionType = Field(..., description="Type of interaction")
    selector: Optional[str] = Field(None, description="Target DOM selector, if applicable")
    value: Optional[Union[str, int, float, bool]] = Field(None, description="Input payload, if applicable")
    timeout_ms: Optional[int] = Field(None, description="Custom wait/timeout limit")
    description: Optional[str] = Field(None, description="Human-readable summary of the action")

class StateSnapshot(BaseModel):
    """A frozen snapshot of a distinct DOM state within a workflow."""

    state_id: str = Field(..., description="Unique snapshot instance ID")
    state_hash: str = Field(..., description="Semantic identity hash of this DOM state")
    url: str = Field(..., description="The current URL")
    timestamp: datetime = Field(..., description="Time this snapshot was captured")
    active_fields: List[FieldSchema] = Field(default_factory=list, description="Fields visible/interactive in this state")
    validation_messages: List[str] = Field(default_factory=list, description="Extracted error/validation messages")

class TransitionSchema(BaseModel):
    """A movement from one DOM state to another caused by an action."""

    transition_id: str = Field(..., description="Unique transition ID")
    from_state_hash: str = Field(..., description="Source state identity")
    to_state_hash: str = Field(..., description="Destination state identity (after action)")
    action_taken: ActionSchema = Field(..., description="The action that caused this transition")
    result: Optional[ResultSchema] = Field(None, description="Underlying execution result, if part of a test case")

class WorkflowNode(BaseModel):
    """A canonical node in the workflow graph representing a unique semantic state."""

    state_hash: str = Field(..., description="Unique semantic state hash")
    first_seen_url: str = Field(..., description="The URL where this state was first encountered")
    visit_count: int = Field(0, description="Number of times the engine has visited this node")
    is_terminal: bool = Field(False, description="Whether this is a final submission/success state")
    edges_out: List[TransitionSchema] = Field(default_factory=list, description="Transitions out of this state")

class WorkflowSession(BaseModel):
    """Persistent tracking object for a multi-step workflow execution run."""

    session_id: str = Field(..., description="Unique workflow session ID")
    run_id: str = Field(..., description="Parent run ID")
    start_time: datetime = Field(..., description="Session start time")
    graph_nodes: Dict[str, WorkflowNode] = Field(default_factory=dict, description="Discovered state graph (hash -> node)")
    navigation_history: List[str] = Field(default_factory=list, description="Chronological list of visited state hashes")
    action_timeline: List[ActionSchema] = Field(default_factory=list, description="Chronological list of actions performed")
    snapshots: Dict[str, StateSnapshot] = Field(default_factory=dict, description="Raw state snapshots by snapshot ID")
