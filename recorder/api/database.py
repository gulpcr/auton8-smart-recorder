"""
Database models and utilities for Auton8 Recorder.
Supports SQLite (local) and PostgreSQL (server deployment).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool

Base = declarative_base()


class ExecutionStatus(str, Enum):
    """Execution status enum."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Step execution status."""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    HEALED = "healed"
    SKIPPED = "skipped"


# =============================================================================
# Database Models
# =============================================================================

class Workflow(Base):
    """Workflow/test case stored in database."""
    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    url = Column(Text, nullable=True)  # Base URL
    steps = Column(JSON, nullable=False, default=list)  # JSON array of steps
    tags = Column(JSON, nullable=False, default=list)  # JSON array of tags

    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = Column(String(255), nullable=True)  # User ID or name

    # Stats (denormalized for performance)
    step_count = Column(Integer, default=0)
    last_run_at = Column(DateTime, nullable=True)
    last_run_status = Column(String(20), nullable=True)
    pass_rate = Column(Float, nullable=True)  # 0.0 to 1.0
    total_runs = Column(Integer, default=0)

    # File reference (for hybrid mode - local file + DB record)
    local_file_path = Column(String(512), nullable=True)

    # Relationships
    executions = relationship("Execution", back_populates="workflow", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_workflows_created_at", "created_at"),
        Index("ix_workflows_last_run_at", "last_run_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "steps": self.steps,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "step_count": self.step_count,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_run_status": self.last_run_status,
            "pass_rate": self.pass_rate,
            "total_runs": self.total_runs,
            "local_file_path": self.local_file_path,
        }


class Execution(Base):
    """Single execution/run of a workflow."""
    __tablename__ = "executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False, index=True)

    # Execution info
    status = Column(String(20), default=ExecutionStatus.PENDING.value, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Configuration
    headless = Column(Boolean, default=True)
    browser = Column(String(50), default="chromium")

    # Results
    total_steps = Column(Integer, default=0)
    passed_steps = Column(Integer, default=0)
    failed_steps = Column(Integer, default=0)
    healed_steps = Column(Integer, default=0)
    skipped_steps = Column(Integer, default=0)

    # Error info
    error_message = Column(Text, nullable=True)
    error_step_index = Column(Integer, nullable=True)

    # Execution environment
    executed_by = Column(String(255), nullable=True)  # User or "api" or "scheduler"
    machine_id = Column(String(255), nullable=True)

    # Relationships
    workflow = relationship("Workflow", back_populates="executions")
    step_results = relationship("StepResult", back_populates="execution", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_executions_started_at", "started_at"),
        Index("ix_executions_workflow_status", "workflow_id", "status"),
    )

    def to_dict(self, include_steps: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow.name if self.workflow else None,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "headless": self.headless,
            "browser": self.browser,
            "total_steps": self.total_steps,
            "passed_steps": self.passed_steps,
            "failed_steps": self.failed_steps,
            "healed_steps": self.healed_steps,
            "skipped_steps": self.skipped_steps,
            "error_message": self.error_message,
            "error_step_index": self.error_step_index,
            "executed_by": self.executed_by,
        }
        if include_steps:
            result["steps"] = [s.to_dict() for s in self.step_results]
        return result


class StepResult(Base):
    """Result of executing a single step."""
    __tablename__ = "step_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id = Column(String(36), ForeignKey("executions.id"), nullable=False, index=True)

    # Step info
    step_index = Column(Integer, nullable=False)
    step_name = Column(String(255), nullable=True)
    step_type = Column(String(50), nullable=False)  # click, input, navigate, etc.

    # Result
    status = Column(String(20), default=StepStatus.PENDING.value, nullable=False)
    duration_ms = Column(Integer, nullable=True)

    # Tiered execution info
    tier_used = Column(Integer, nullable=True)  # 0, 1, 2, or 3
    tier_name = Column(String(50), nullable=True)  # "Playwright", "Healing", "CV", "LLM"

    # Healing info (if healed)
    was_healed = Column(Boolean, default=False)
    healing_strategy = Column(String(50), nullable=True)
    original_selector = Column(Text, nullable=True)
    healed_selector = Column(Text, nullable=True)
    healing_confidence = Column(Float, nullable=True)

    # Error info
    error_message = Column(Text, nullable=True)

    # Screenshot reference
    screenshot_path = Column(String(512), nullable=True)

    # Raw details (for debugging)
    details = Column(JSON, nullable=True)

    # Relationships
    execution = relationship("Execution", back_populates="step_results")

    __table_args__ = (
        Index("ix_step_results_execution_index", "execution_id", "step_index"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "step_index": self.step_index,
            "step_name": self.step_name,
            "step_type": self.step_type,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "tier_used": self.tier_used,
            "tier_name": self.tier_name,
            "was_healed": self.was_healed,
            "healing_strategy": self.healing_strategy,
            "original_selector": self.original_selector,
            "healed_selector": self.healed_selector,
            "healing_confidence": self.healing_confidence,
            "error_message": self.error_message,
            "screenshot_path": self.screenshot_path,
            "details": self.details,
        }


class MLTrainingData(Base):
    """Training data collected for ML models."""
    __tablename__ = "ml_training_data"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    data_type = Column(String(50), nullable=False, index=True)  # "selector", "healing"

    # Features (stored as JSON for flexibility)
    features = Column(JSON, nullable=False)

    # Outcome
    success = Column(Boolean, nullable=False)
    outcome_details = Column(JSON, nullable=True)  # Additional outcome info

    # Context
    workflow_id = Column(String(36), nullable=True)
    execution_id = Column(String(36), nullable=True)
    step_index = Column(Integer, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    url = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_ml_training_data_type_created", "data_type", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "data_type": self.data_type,
            "features": self.features,
            "success": self.success,
            "outcome_details": self.outcome_details,
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "step_index": self.step_index,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "url": self.url,
        }


# =============================================================================
# Database Connection Management
# =============================================================================

class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            database_url: Database URL. If None, uses SQLite in data/recorder.db
        """
        if database_url is None:
            # Default to SQLite
            data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "recorder.db")
            database_url = f"sqlite:///{db_path}"

        self.database_url = database_url

        # Create engine with appropriate settings
        if database_url.startswith("sqlite"):
            # SQLite-specific settings for thread safety
            self.engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False
            )
        else:
            # PostgreSQL or other databases
            self.engine = create_engine(database_url, echo=False)

        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Create tables
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def close(self):
        """Close database connection."""
        self.engine.dispose()


# =============================================================================
# Repository Classes (Data Access Layer)
# =============================================================================

class WorkflowRepository:
    """Repository for workflow operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, workflow_data: Dict[str, Any]) -> Workflow:
        """Create a new workflow."""
        workflow = Workflow(**workflow_data)
        self.session.add(workflow)
        self.session.commit()
        self.session.refresh(workflow)
        return workflow

    def get_by_id(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID."""
        return self.session.query(Workflow).filter(Workflow.id == workflow_id).first()

    def get_by_name(self, name: str) -> Optional[Workflow]:
        """Get workflow by name."""
        return self.session.query(Workflow).filter(Workflow.name == name).first()

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Workflow]:
        """List all workflows."""
        return self.session.query(Workflow).order_by(Workflow.updated_at.desc()).offset(offset).limit(limit).all()

    def search(self, query: str, tags: Optional[List[str]] = None) -> List[Workflow]:
        """Search workflows by name or tags."""
        q = self.session.query(Workflow)
        if query:
            q = q.filter(Workflow.name.ilike(f"%{query}%"))
        # Note: Tag filtering would require JSON operations specific to the database
        return q.order_by(Workflow.updated_at.desc()).all()

    def update(self, workflow_id: str, data: Dict[str, Any]) -> Optional[Workflow]:
        """Update a workflow."""
        workflow = self.get_by_id(workflow_id)
        if workflow:
            for key, value in data.items():
                if hasattr(workflow, key):
                    setattr(workflow, key, value)
            self.session.commit()
            self.session.refresh(workflow)
        return workflow

    def delete(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        workflow = self.get_by_id(workflow_id)
        if workflow:
            self.session.delete(workflow)
            self.session.commit()
            return True
        return False

    def update_stats(self, workflow_id: str, execution: Execution):
        """Update workflow stats after execution."""
        workflow = self.get_by_id(workflow_id)
        if workflow:
            workflow.total_runs = (workflow.total_runs or 0) + 1
            workflow.last_run_at = execution.completed_at or execution.started_at
            workflow.last_run_status = execution.status

            # Recalculate pass rate
            total = self.session.query(Execution).filter(
                Execution.workflow_id == workflow_id,
                Execution.status.in_([ExecutionStatus.COMPLETED.value, ExecutionStatus.FAILED.value])
            ).count()

            passed = self.session.query(Execution).filter(
                Execution.workflow_id == workflow_id,
                Execution.status == ExecutionStatus.COMPLETED.value,
                Execution.failed_steps == 0
            ).count()

            workflow.pass_rate = passed / total if total > 0 else None
            self.session.commit()


class ExecutionRepository:
    """Repository for execution operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, execution_data: Dict[str, Any]) -> Execution:
        """Create a new execution."""
        execution = Execution(**execution_data)
        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)
        return execution

    def get_by_id(self, execution_id: str) -> Optional[Execution]:
        """Get execution by ID."""
        return self.session.query(Execution).filter(Execution.id == execution_id).first()

    def list_for_workflow(self, workflow_id: str, limit: int = 50) -> List[Execution]:
        """List executions for a workflow."""
        return self.session.query(Execution).filter(
            Execution.workflow_id == workflow_id
        ).order_by(Execution.started_at.desc()).limit(limit).all()

    def list_recent(self, limit: int = 50, status: Optional[str] = None) -> List[Execution]:
        """List recent executions."""
        q = self.session.query(Execution)
        if status:
            q = q.filter(Execution.status == status)
        return q.order_by(Execution.started_at.desc()).limit(limit).all()

    def update(self, execution_id: str, data: Dict[str, Any]) -> Optional[Execution]:
        """Update an execution."""
        execution = self.get_by_id(execution_id)
        if execution:
            for key, value in data.items():
                if hasattr(execution, key):
                    setattr(execution, key, value)
            self.session.commit()
            self.session.refresh(execution)
        return execution

    def add_step_result(self, execution_id: str, step_data: Dict[str, Any]) -> StepResult:
        """Add a step result to an execution."""
        step_result = StepResult(execution_id=execution_id, **step_data)
        self.session.add(step_result)
        self.session.commit()
        self.session.refresh(step_result)
        return step_result

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        total = self.session.query(Execution).count()
        completed = self.session.query(Execution).filter(Execution.status == ExecutionStatus.COMPLETED.value).count()
        failed = self.session.query(Execution).filter(Execution.status == ExecutionStatus.FAILED.value).count()

        # Healing stats
        healed_steps = self.session.query(StepResult).filter(StepResult.was_healed == True).count()
        total_steps = self.session.query(StepResult).count()

        return {
            "total_runs": total,
            "completed_runs": completed,
            "failed_runs": failed,
            "pass_rate": completed / total if total > 0 else 0,
            "total_steps_executed": total_steps,
            "healed_steps": healed_steps,
            "healing_rate": healed_steps / total_steps if total_steps > 0 else 0,
        }


class MLTrainingDataRepository:
    """Repository for ML training data operations."""

    def __init__(self, session: Session):
        self.session = session

    def add(self, data: Dict[str, Any]) -> MLTrainingData:
        """Add training data."""
        record = MLTrainingData(**data)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_by_type(self, data_type: str, limit: int = 1000) -> List[MLTrainingData]:
        """Get training data by type."""
        return self.session.query(MLTrainingData).filter(
            MLTrainingData.data_type == data_type
        ).order_by(MLTrainingData.created_at.desc()).limit(limit).all()

    def get_stats(self) -> Dict[str, Any]:
        """Get training data statistics."""
        selector_count = self.session.query(MLTrainingData).filter(
            MLTrainingData.data_type == "selector"
        ).count()
        healing_count = self.session.query(MLTrainingData).filter(
            MLTrainingData.data_type == "healing"
        ).count()

        selector_success = self.session.query(MLTrainingData).filter(
            MLTrainingData.data_type == "selector",
            MLTrainingData.success == True
        ).count()
        healing_success = self.session.query(MLTrainingData).filter(
            MLTrainingData.data_type == "healing",
            MLTrainingData.success == True
        ).count()

        return {
            "selector_samples": selector_count,
            "selector_success_rate": selector_success / selector_count if selector_count > 0 else 0,
            "healing_samples": healing_count,
            "healing_success_rate": healing_success / healing_count if healing_count > 0 else 0,
        }

    def clear(self, data_type: Optional[str] = None):
        """Clear training data."""
        q = self.session.query(MLTrainingData)
        if data_type:
            q = q.filter(MLTrainingData.data_type == data_type)
        q.delete()
        self.session.commit()


# =============================================================================
# Global instance (for simple use cases)
# =============================================================================

_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get or create the global database manager."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_session() -> Session:
    """Get a new database session from the global manager."""
    return get_db_manager().get_session()
