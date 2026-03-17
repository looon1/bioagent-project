"""
Worktree coordinator for cross-worktree task coordination.

Manages resource sharing and coordination between worktrees.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from bioagent.observability import Logger
from bioagent.worktree.manager import WorktreeManager


class WorktreeCoordinator:
    """
    Coordinates worktrees for cross-worktree operations.

    Provides:
    - Resource sharing between worktrees
    - Status synchronization
    - Conflict detection
    """

    def __init__(
        self,
        worktree_manager: WorktreeManager,
        logger: Optional[Logger] = None
    ):
        """
        Initialize WorktreeCoordinator.

        Args:
            worktree_manager: WorktreeManager instance
            logger: Optional logger for logging operations
        """
        self.worktree_manager = worktree_manager
        self.logger = logger or Logger("worktree_coordinator")

        # Shared resources registry
        self.shared_resources: Dict[str, Dict[str, Any]] = {}

        # Resource locks
        self.resource_locks: Dict[str, str] = {}  # resource -> worktree_name

        self.logger.info("WorktreeCoordinator initialized")

    def register_shared_resource(
        self,
        resource_id: str,
        resource_type: str,
        worktree_name: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register a shared resource.

        Args:
            resource_id: Unique resource identifier
            resource_type: Type of resource (e.g., "file", "dataset", "model")
            worktree_name: Worktree that owns the resource
            data: Optional resource metadata

        Returns:
            True if registered successfully
        """
        if resource_id in self.shared_resources:
            self.logger.warning(
                f"Resource {resource_id} already registered",
                resource_id=resource_id
            )
            return False

        self.shared_resources[resource_id] = {
            "type": resource_type,
            "owner": worktree_name,
            "data": data or {},
            "registered_at": self._get_timestamp()
        }

        self.logger.debug(
            f"Registered shared resource {resource_id}",
            resource_id=resource_id,
            resource_type=resource_type,
            owner=worktree_name
        )

        return True

    def get_shared_resource(
        self,
        resource_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a shared resource.

        Args:
            resource_id: Resource identifier

        Returns:
            Resource data if found, None otherwise
        """
        return self.shared_resources.get(resource_id)

    def list_shared_resources(
        self,
        worktree_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List shared resources.

        Args:
            worktree_name: Optional filter by owner worktree

        Returns:
            List of resource dictionaries
        """
        resources = []

        for rid, data in self.shared_resources.items():
            if worktree_name is None or data.get("owner") == worktree_name:
                resources.append({
                    "id": rid,
                    **data
                })

        return resources

    def acquire_lock(
        self,
        resource_id: str,
        worktree_name: str
    ) -> bool:
        """
        Acquire a lock on a resource.

        Args:
            resource_id: Resource to lock
            worktree_name: Worktree requesting the lock

        Returns:
            True if lock acquired, False if already locked
        """
        if resource_id in self.resource_locks:
            owner = self.resource_locks[resource_id]
            if owner != worktree_name:
                self.logger.warning(
                    f"Resource {resource_id} locked by {owner}",
                    resource_id=resource_id,
                    locked_by=owner,
                    requested_by=worktree_name
                )
                return False

        self.resource_locks[resource_id] = worktree_name
        self.logger.debug(
            f"Acquired lock on {resource_id}",
            resource_id=resource_id,
            worktree_name=worktree_name
        )

        return True

    def release_lock(
        self,
        resource_id: str,
        worktree_name: str
    ) -> bool:
        """
        Release a lock on a resource.

        Args:
            resource_id: Resource to unlock
            worktree_name: Worktree releasing the lock

        Returns:
            True if lock released, False if not the owner
        """
        if resource_id not in self.resource_locks:
            return True  # Not locked, nothing to release

        owner = self.resource_locks[resource_id]
        if owner != worktree_name:
            self.logger.warning(
                f"Cannot release lock: {resource_id} owned by {owner}",
                resource_id=resource_id,
                locked_by=owner,
                requested_by=worktree_name
            )
            return False

        del self.resource_locks[resource_id]
        self.logger.debug(
            f"Released lock on {resource_id}",
            resource_id=resource_id,
            worktree_name=worktree_name
        )

        return True

    def detect_conflicts(
        self,
        worktree_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Detect potential conflicts between worktrees.

        Args:
            worktree_names: List of worktree names to check

        Returns:
            List of conflict descriptions
        """
        conflicts = []
        worktrees = self.worktree_manager.list_all()

        # Group by base branch
        branch_groups = {}
        for wt in worktrees:
            if wt["name"] in worktree_names:
                branch = wt.get("branch", "")
                if branch not in branch_groups:
                    branch_groups[branch] = []
                branch_groups[branch].append(wt["name"])

        # Check for branch conflicts
        for branch, names in branch_groups.items():
            if len(names) > 1:
                conflicts.append({
                    "type": "branch_conflict",
                    "branch": branch,
                    "worktrees": names,
                    "description": f"Multiple worktrees on same branch: {', '.join(names)}"
                })

        # Check for locked resources
        for resource, owner in self.resource_locks.items():
            if owner in worktree_names:
                conflicts.append({
                    "type": "locked_resource",
                    "resource": resource,
                    "owner": owner,
                    "description": f"Resource '{resource}' locked by {owner}"
                })

        return conflicts

    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()

    def get_status(self) -> Dict[str, Any]:
        """
        Get coordinator status.

        Returns:
            Dictionary with coordinator information
        """
        return {
            "shared_resources": len(self.shared_resources),
            "active_locks": len(self.resource_locks),
            "locked_resources": list(self.resource_locks.keys()),
        }
