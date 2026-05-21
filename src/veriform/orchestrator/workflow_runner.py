"""
veriform.orchestrator.workflow_runner
=====================================
Stateful multi-step workflow execution engine.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

from veriform.config import settings
from veriform.detector.state_tracker import capture_state
from veriform.executor.action_engine import ActionEngine
from veriform.models.schemas import TestCaseSchema
from veriform.models.workflow import ActionSchema, TransitionSchema, WorkflowNode, WorkflowSession
from veriform.utils.logging import get_logger

logger = get_logger(__name__)


async def run_workflow(
    target_url: str,
    page: Any,
) -> WorkflowSession:
    """Execute test cases within a stateful workflow session using DFS graph traversal."""
    run_id = str(uuid.uuid4())
    session = WorkflowSession(
        session_id=str(uuid.uuid4()),
        run_id=run_id,
        start_time=datetime.now(tz=timezone.utc),
    )
    
    engine = ActionEngine(page)
    
    # Each item is a trace of actions to replay to reach a state to explore
    # Initial state is reached by a single navigation action
    nav_action = ActionSchema(
        action_id=f"act_{uuid.uuid4().hex[:8]}",
        type="navigate",
        value=target_url,
        description=f"Navigate to {target_url}"
    )
    queue: list[list[ActionSchema]] = [[nav_action]]
    
    states_explored = 0
    
    while queue and states_explored < settings.max_states_explored:
        trace = queue.pop()
        
        # 1. Replay trace to reach target state
        try:
            for action in trace:
                await engine.execute_action(action)
                session.action_timeline.append(action)
        except Exception as exc:
            logger.warning("Trace replay failed: %s", exc)
            continue
            
        # 2. Capture state
        current_state = await capture_state(page, run_id)
        if current_state.state_hash not in session.snapshots:
            session.snapshots[current_state.state_hash] = current_state
            
        session.navigation_history.append(current_state.state_hash)
        _ensure_node(session, current_state.state_hash, page.url)
        
        node = session.graph_nodes[current_state.state_hash]
        
        # Loop prevention: Don't explore this node if already visited (beyond initial capture)
        if node.visit_count > 1:
            continue
            
        states_explored += 1
        
        # If we reached max depth, stop exploring this branch
        if len(trace) >= settings.max_workflow_depth:
            continue
            
        # 3. Detect fields and generate next actions
        # For a full implementation we would call the orchestrator's ML and generation steps here
        # to generate candidates. For now, we will create generic fill + submit actions.
        # This allows us to map the state graph.
        
        if not current_state.active_fields:
            node.is_terminal = True
            continue
            
        # Create a single default transition to explore the 'happy path'
        next_actions = []
        for field in current_state.active_fields:
            val = "test@example.com" if field.type == "email" else "test"
            next_actions.append(ActionSchema(
                action_id=f"act_{uuid.uuid4().hex[:8]}",
                type="fill",
                selector=f"[name='{field.name}']" if field.name else f"#{field.dom_id}",
                value=val,
            ))
            
        next_actions.append(ActionSchema(
            action_id=f"act_{uuid.uuid4().hex[:8]}",
            type="submit",
        ))
        next_actions.append(ActionSchema(
            action_id=f"act_{uuid.uuid4().hex[:8]}",
            type="wait",
        ))
        
        # Append this new sequence to the queue
        new_trace = trace + next_actions
        queue.append(new_trace)
        
    return session

def _ensure_node(session: WorkflowSession, state_hash: str, url: str) -> None:
    if state_hash not in session.graph_nodes:
        session.graph_nodes[state_hash] = WorkflowNode(
            state_hash=state_hash,
            first_seen_url=url,
        )
    session.graph_nodes[state_hash].visit_count += 1
