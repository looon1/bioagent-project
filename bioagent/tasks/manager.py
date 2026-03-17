"""
TaskManager for persistent task storage and dependency management.

Provides file-based persistence for tasks with JSON backing,
and manages dependency relationships between tasks.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from bioagent.observability import Logger
from bioagent.tasks.models import Task, TaskPriority, TaskStatus


class TaskManager:
    """
    Manages persistent task storage with JSON file backing.

    Tasks are stored as individual JSON files in a directory,
    with in-memory caching for fast access.
    """

    def __init__(self, tasks_dir: Path, logger: Optional[Logger] = None):
        """
        Initialize the TaskManager.

        Args:
            tasks_dir: Directory to store task JSON files
            logger: Optional logger for logging operations
        """
        self.tasks_dir = Path(tasks_dir)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Task] = {}
        self.logger = logger or Logger("task_manager")

        # Load existing tasks on initialization
        self._load_all_tasks()

    def _load_all_tasks(self) -> None:
        """Load all tasks from disk into cache."""
        for task_file in self.tasks_dir.glob("*.json"):
            try:
                with open(task_file, "r") as f:
                    data = json.load(f)
                    task = Task.from_dict(data)
                    self._cache[task.id] = task
            except Exception as e:
                self.logger.warning(
                    f"Failed to load task from {task_file}: {e}",
                    task_file=str(task_file)
                )

        self.logger.info(
            f"Loaded {len(self._cache)} tasks from {self.tasks_dir}",
            tasks_dir=str(self.tasks_dir)
        )

    def _save_task(self, task: Task) -> None:
        """
        Save a task to disk.

        Args:
            task: Task to save
        """
        task_file = self.tasks_dir / f"{task.id}.json"
        with open(task_file, "w") as f:
            json.dump(task.to_dict(), f, indent=2)

    def create_task(
        self,
        subject: str,
        description: str,
        active_form: str = "",
        priority: str = "medium",
        owner: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """
        Create a new task.

        Args:
            subject: Brief title of the task
            description: Detailed description of the task
            active_form: Present continuous form for display
            priority: Priority level (low, medium, high, critical)
            owner: Optional agent ID that owns this task
            metadata: Additional key-value information

        Returns:
            The created Task instance
        """
        # Convert string to TaskPriority enum
        task_priority = TaskPriority(priority)

        task = Task(
            id=str(uuid.uuid4()),
            subject=subject,
            description=description,
            active_form=active_form,
            priority=task_priority,
            owner=owner,
            metadata=metadata or {},
        )

        self._cache[task.id] = task
        self._save_task(task)

        self.logger.info(
            f"Created task: {task.id}",
            task_id=task.id,
            subject=subject,
            priority=priority
        )

        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Retrieve a task by ID.

        Args:
            task_id: Unique identifier of the task

        Returns:
            Task instance if found, None otherwise
        """
        return self._cache.get(task_id)

    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        description: Optional[str] = None,
        active_form: Optional[str] = None,
    ) -> Optional[Task]:
        """
        Update a task's fields.

        Args:
            task_id: Unique identifier of the task
            status: New status if provided
            priority: New priority if provided
            description: New description if provided
            active_form: New active form if provided

        Returns:
            Updated Task instance if found, None otherwise
        """
        task = self._cache.get(task_id)
        if not task:
            self.logger.warning(
                f"Task not found for update: {task_id}",
                task_id=task_id
            )
            return None

        from bioagent.tasks.models import TaskPriority

        if status:
            task.status = TaskStatus(status)
            if task.status == TaskStatus.COMPLETED and not task.completed_at:
                from datetime import datetime
                task.completed_at = datetime.now(timezone.utc)
        if priority:
            task.priority = TaskPriority(priority)
        if description:
            task.description = description
        if active_form:
            task.active_form = active_form

        from datetime import datetime
        task.updated_at = datetime.now(timezone.utc)

        self._save_task(task)

        self.logger.info(
            f"Updated task: {task_id}",
            task_id=task_id,
            status=status,
            priority=priority
        )

        return task

    def delete_task(self, task_id: str, cleanup: bool = True) -> bool:
        """
        Delete a task and clean up references.

        Args:
            task_id: Unique identifier of the task
            cleanup: If True, remove task from blocked_by lists of dependent tasks

        Returns:
            True if task was deleted, False otherwise
        """
        task = self._cache.get(task_id)
        if not task:
            self.logger.warning(
                f"Task not found for deletion: {task_id}",
                task_id=task_id
            )
            return False

        # Remove from blocked_by lists of dependent tasks
        if cleanup:
            for blocked_id in task.blocks:
                blocked_task = self._cache.get(blocked_id)
                if blocked_task and task_id in blocked_task.blocked_by:
                    blocked_task.blocked_by.remove(task_id)
                    self._save_task(blocked_task)

        # Remove from blocks lists of blocking tasks
        for blocking_id in task.blocked_by:
            blocking_task = self._cache.get(blocking_id)
            if blocking_task and task_id in blocking_task.blocks:
                blocking_task.blocks.remove(task_id)
                self._save_task(blocking_task)

        # Delete from cache and disk
        del self._cache[task_id]
        task_file = self.tasks_dir / f"{task_id}.json"
        if task_file.exists():
            task_file.unlink()

        self.logger.info(
            f"Deleted task: {task_id}",
            task_id=task_id
        )

        return True

    def list_tasks(
        self,
        status: Optional[str] = None,
        owner: Optional[str] = None,
        priority: Optional[str] = None,
        exclude_deleted: bool = True,
    ) -> List[Task]:
        """
        List tasks with optional filtering.

        Args:
            status: Filter by status
            owner: Filter by owner
            priority: Filter by priority
            exclude_deleted: Exclude deleted tasks

        Returns:
            List of Task instances matching filters
        """
        tasks = list(self._cache.values())

        if exclude_deleted:
            tasks = [t for t in tasks if t.status != TaskStatus.DELETED]

        if status:
            tasks = [t for t in tasks if t.status.value == status]

        if owner:
            tasks = [t for t in tasks if t.owner == owner]

        if priority:
            tasks = [t for t in tasks if t.priority.value == priority]

        # Sort by created_at (newest first)
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        return tasks

    def add_dependency(self, task_id: str, blocking_id: str) -> bool:
        """
        Add a dependency relationship between tasks.

        Task `task_id` will be blocked by task `blocking_id`.

        Args:
            task_id: ID of the task to be blocked
            blocking_id: ID of the blocking task

        Returns:
            True if dependency was added, False if it would create a cycle
        """
        if task_id == blocking_id:
            self.logger.warning(
                "Cannot add self-dependency",
                task_id=task_id
            )
            return False

        if blocking_id not in self._cache:
            self.logger.warning(
                f"Blocking task not found: {blocking_id}",
                task_id=task_id,
                blocking_id=blocking_id
            )
            return False

        if task_id not in self._cache:
            self.logger.warning(
                f"Task not found: {task_id}",
                task_id=task_id,
                blocking_id=blocking_id
            )
            return False

        # Check for circular dependency
        if self._would_create_cycle(task_id, blocking_id):
            self.logger.warning(
                "Cannot add dependency: would create circular dependency",
                task_id=task_id,
                blocking_id=blocking_id
            )
            return False

        task = self._cache[task_id]
        blocking_task = self._cache[blocking_id]

        # Add relationship
        if blocking_id not in task.blocked_by:
            task.blocked_by.append(blocking_id)
        if task_id not in blocking_task.blocks:
            blocking_task.blocks.append(task_id)

        self._save_task(task)
        self._save_task(blocking_task)

        self.logger.info(
            f"Added dependency: {task_id} blocked by {blocking_id}",
            task_id=task_id,
            blocking_id=blocking_id
        )

        return True

    def remove_dependency(self, task_id: str, blocking_id: str) -> bool:
        """
        Remove a dependency relationship between tasks.

        Args:
            task_id: ID of the blocked task
            blocking_id: ID of the blocking task

        Returns:
            True if dependency was removed, False otherwise
        """
        task = self._cache.get(task_id)
        blocking_task = self._cache.get(blocking_id)

        if not task or not blocking_task:
            return False

        removed = False

        if blocking_id in task.blocked_by:
            task.blocked_by.remove(blocking_id)
            removed = True
        if task_id in blocking_task.blocks:
            blocking_task.blocks.remove(task_id)
            removed = True

        if removed:
            self._save_task(task)
            self._save_task(blocking_task)

            self.logger.info(
                f"Removed dependency: {task_id} no longer blocked by {blocking_id}",
                task_id=task_id,
                blocking_id=blocking_id
            )

        return removed

    def resolve_dependencies(self, task_id: str) -> int:
        """
        Resolve dependencies after a task completes.

        Checks all tasks blocked by the completed task and unblocks
        those where all blocking tasks are now completed.

        Args:
            task_id: ID of the completed task

        Returns:
            Number of tasks that were unblocked
        """
        task = self._cache.get(task_id)
        if not task:
            return 0

        unblocked_count = 0

        for blocked_id in task.blocks:
            blocked_task = self._cache.get(blocked_id)
            if not blocked_task:
                continue

            # Check if all blocking tasks are completed
            all_blocking_complete = True
            for blocking_id in blocked_task.blocked_by:
                blocking_task = self._cache.get(blocking_id)
                if not blocking_task or blocking_task.status != TaskStatus.COMPLETED:
                    all_blocking_complete = False
                    break

            if all_blocking_complete and task_id in blocked_task.blocked_by:
                # Unblock this task
                blocked_task.blocked_by.remove(task_id)
                self._save_task(blocked_task)
                unblocked_count += 1

                self.logger.info(
                    f"Unblocked task: {blocked_id}",
                    task_id=blocked_id,
                    unblocked_by=task_id
                )

        return unblocked_count

    def get_pending_tasks(self, owner: Optional[str] = None) -> List[Task]:
        """
        Get all pending tasks that are not blocked.

        Args:
            owner: Optional filter by owner

        Returns:
            List of pending, unblocked tasks sorted by priority
        """
        tasks = self.list_tasks(status="pending", owner=owner)

        # Filter out blocked tasks
        tasks = [t for t in tasks if not t.is_blocked()]

        # Sort by priority (critical > high > medium > low)
        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
        }
        tasks.sort(key=lambda t: priority_order.get(t.priority.value, 99))

        return tasks

    def get_next_pending_task(self, owner: Optional[str] = None) -> Optional[Task]:
        """
        Get the highest priority pending task.

        Args:
            owner: Optional filter by owner

        Returns:
            Highest priority pending task, or None if no tasks available
        """
        pending = self.get_pending_tasks(owner)
        return pending[0] if pending else None

    def _would_create_cycle(self, task_id: str, blocking_id: str) -> bool:
        """
        Check if adding a dependency would create a cycle using DFS.

        Args:
            task_id: ID of the task to be blocked
            blocking_id: ID of the blocking task

        Returns:
            True if adding the dependency would create a cycle
        """
        visited = set()

        def dfs(current_id: str) -> bool:
            """DFS to check for cycles."""
            if current_id == task_id:
                return True  # Found a cycle
            if current_id in visited:
                return False

            visited.add(current_id)

            current = self._cache.get(current_id)
            if not current:
                return False

            for dep_id in current.blocked_by:
                if dfs(dep_id):
                    return True

            return False

        return dfs(blocking_id)

    def cleanup_old_tasks(self, days: int = 7) -> int:
        """
        Delete completed tasks older than specified days.

        Args:
            days: Number of days after which to delete completed tasks

        Returns:
            Number of tasks deleted
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        deleted_count = 0

        for task_id, task in list(self._cache.items()):
            if (
                task.status == TaskStatus.COMPLETED
                and task.completed_at
                and task.completed_at < cutoff
            ):
                self.delete_task(task_id)
                deleted_count += 1

        if deleted_count > 0:
            self.logger.info(
                f"Cleaned up {deleted_count} completed tasks older than {days} days",
                days=days,
                deleted_count=deleted_count
            )

        return deleted_count

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all tasks.

        Returns:
            Dictionary with task statistics
        """
        all_tasks = list(self._cache.values())

        summary = {
            "total": len(all_tasks),
            "pending": sum(1 for t in all_tasks if t.status == TaskStatus.PENDING),
            "in_progress": sum(1 for t in all_tasks if t.status == TaskStatus.IN_PROGRESS),
            "completed": sum(1 for t in all_tasks if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in all_tasks if t.status == TaskStatus.FAILED),
            "deleted": sum(1 for t in all_tasks if t.status == TaskStatus.DELETED),
            "blocked": sum(1 for t in all_tasks if t.is_blocked()),
        }

        return summary
