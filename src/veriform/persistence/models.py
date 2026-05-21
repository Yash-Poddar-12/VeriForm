"""
veriform.persistence.models
===========================
SQLAlchemy 2.0 ORM definitions for workflow execution tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veriform.persistence.database import Base


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _uuid4() -> str:
    return str(uuid.uuid4())


class WorkflowRun(Base):
    """A complete workflow execution session."""
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # pending, running, completed, failed
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_duration_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    # Relationships
    states: Mapped[list["WorkflowState"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    transitions: Mapped[list["WorkflowTransition"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    events: Mapped[list["ExecutionEvent"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    artifacts: Mapped[list["WorkflowArtifact"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class WorkflowState(Base):
    """A unique semantic state discovered during a run."""
    __tablename__ = "workflow_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4)
    run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False, index=True)
    state_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    first_seen_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    visit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    run: Mapped["WorkflowRun"] = relationship(back_populates="states")
    
    # Optional: store full active fields and validation messages
    state_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)


class WorkflowTransition(Base):
    """A movement from one WorkflowState to another via an action."""
    __tablename__ = "workflow_transitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4)
    run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False, index=True)
    from_state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    to_state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    
    result_status: Mapped[str] = mapped_column(String(50), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    run: Mapped["WorkflowRun"] = relationship(back_populates="transitions")


class ExecutionEvent(Base):
    """Deterministic timeline event for replay and debugging."""
    __tablename__ = "execution_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4)
    run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # e.g. "action_started", "snapshot_captured", "error"
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    run: Mapped["WorkflowRun"] = relationship(back_populates="events")


class WorkflowArtifact(Base):
    """Reference to file-backed artifacts (screenshots, traces)."""
    __tablename__ = "workflow_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4)
    run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # e.g. "screenshot", "trace", "report"
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    run: Mapped["WorkflowRun"] = relationship(back_populates="artifacts")
