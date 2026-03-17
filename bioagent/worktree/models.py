"""
Worktree data models for BioAgent worktree system.

Defines core data structures for worktree tracking including
WorktreeStatus enum and Worktree dataclass.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


class WorktreeStatus(str, Enum):
    """Status of a worktree in worktree system."""

    ACTIVE = "active"
    REMOVED = "removed"
    KEPT = "kept"
    ORPHANED = "orphaned"


@dataclass
class Worktree:
    """
    Represents a git worktree in BioAgent system.

    Attributes:
        name: Unique identifier/name of the worktree
        path: Absolute path to the worktree directory
        branch: Git branch name for this worktree
        task_id: Optional task ID that this worktree is bound to
        status: Current status of the worktree
        base_ref: Git reference this worktree was created from
        created_at: Timestamp when worktree was created
        updated_at: Timestamp when worktree was last updated
        removed_at: Optional timestamp when worktree was removed
        kept_at: Optional timestamp when worktree was marked as kept
        metadata: Additional key-value information about worktree
    """

    name: str
    path: Path
    branch: str
    task_id: Optional[str] = None
    status: WorktreeStatus = WorktreeStatus.ACTIVE
    base_ref: str = "HEAD"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    removed_at: Optional[datetime] = None
    kept_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert worktree to a dictionary for JSON serialization.

        Returns:
            Dictionary representation of worktree
        """
        return {
            "name": self.name,
            "path": str(self.path),
            "branch": self.branch,
            "task_id": self.task_id,
            "status": self.status.value,
            "base_ref": self.base_ref,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "removed_at": self.removed_at.isoformat() if self.removed_at else None,
            "kept_at": self.kept_at.isoformat() if self.kept_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Worktree":
        """
        Create a Worktree from a dictionary.

        Args:
            data: Dictionary representation of worktree

        Returns:
            Worktree instance
        """
        # Handle datetime fields
        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        updated_at = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc)
        removed_at = datetime.fromisoformat(data["removed_at"]) if data.get("removed_at") else None
        kept_at = datetime.fromisoformat(data["kept_at"]) if data.get("kept_at") else None

        return cls(
            name=data["name"],
            path=Path(data["path"]),
            branch=data["branch"],
            task_id=data.get("task_id"),
            status=WorktreeStatus(data.get("status", "active")),
            base_ref=data.get("base_ref", "HEAD"),
            metadata=data.get("metadata", {}),
            created_at=created_at,
            updated_at=updated_at,
            removed_at=removed_at,
            kept_at=kept_at,
        )

    def is_active(self) -> bool:
        """Check if this worktree is active."""
        return self.status == WorktreeStatus.ACTIVE

    def is_removed(self) -> bool:
        """Check if this worktree has been removed."""
        return self.status == WorktreeStatus.REMOVED

    def is_kept(self) -> bool:
        """Check if this worktree is marked as kept."""
        return self.status == WorktreeStatus.KEPT
