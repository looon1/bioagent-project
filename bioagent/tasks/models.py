"""
Task data models for BioAgent task system.

Defines the core data structures for task tracking including
TaskStatus enum, TaskPriority enum, and Task dataclass.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    """Status of a task in the task system."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"


class TaskPriority(str, Enum):
    """Priority levels for tasks."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Task:
    """
    Represents a task in the BioAgent task system.

    Attributes:
        id: Unique identifier for the task
        subject: Brief title of the task
        description: Detailed description of what needs to be done
        active_form: Present continuous form for display (e.g., "Analyzing data")
        status: Current status of the task
        priority: Priority level of the task
        blocked_by: List of task IDs that must complete before this task can start
        blocks: List of task IDs that are blocked by this task
        owner: Optional agent ID that owns this task
        metadata: Additional key-value information about the task
        created_at: Timestamp when the task was created
        updated_at: Timestamp when the task was last updated
        completed_at: Timestamp when the task was completed (if applicable)
    """

    id: str
    subject: str
    description: str
    active_form: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    blocked_by: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    owner: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the task to a dictionary for JSON serialization.

        Returns:
            Dictionary representation of the task
        """
        return {
            "id": self.id,
            "subject": self.subject,
            "description": self.description,
            "active_form": self.active_form,
            "status": self.status.value,
            "priority": self.priority.value,
            "blocked_by": self.blocked_by,
            "blocks": self.blocks,
            "owner": self.owner,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """
        Create a Task from a dictionary.

        Args:
            data: Dictionary representation of the task

        Returns:
            Task instance
        """
        # Handle datetime fields
        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        updated_at = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc)
        completed_at = datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None

        return cls(
            id=data["id"],
            subject=data["subject"],
            description=data["description"],
            active_form=data.get("active_form", ""),
            status=TaskStatus(data.get("status", "pending")),
            priority=TaskPriority(data.get("priority", "medium")),
            blocked_by=data.get("blocked_by", []),
            blocks=data.get("blocks", []),
            owner=data.get("owner"),
            metadata=data.get("metadata", {}),
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
        )

    def is_blocked(self) -> bool:
        """Check if this task is blocked by other tasks."""
        return len(self.blocked_by) > 0

    def can_start(self) -> bool:
        """Check if this task can be started (pending and not blocked)."""
        return self.status == TaskStatus.PENDING and not self.is_blocked()
