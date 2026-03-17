"""
TodoWrite tool for in-memory task planning and tracking.

Provides an in-memory task management system with optional persistence
via TaskManager. Includes tool wrappers for agent integration.
"""

from typing import Any, Dict, List, Optional

from bioagent.observability import Logger
from bioagent.tasks.manager import TaskManager
from bioagent.tasks.models import Task, TaskPriority, TaskStatus


class TodoWrite:
    """
    In-memory task planning and tracking system.

    Wraps TaskManager for task operations and provides
    methods for task querying and management.
    """

    def __init__(self, task_manager: TaskManager, logger: Optional[Logger] = None):
        """
        Initialize TodoWrite.

        Args:
            task_manager: TaskManager instance for persistence
            logger: Optional logger for logging operations
        """
        self.task_manager = task_manager
        self.logger = logger or Logger("todo_write")

    def create(
        self,
        subject: str,
        description: str,
        active_form: str = "",
        priority: str = "medium",
        persist: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a new task.

        Args:
            subject: Brief title of the task
            description: Detailed description of the task
            active_form: Present continuous form for display
            priority: Priority level (low, medium, high, critical)
            persist: Whether to persist the task to disk

        Returns:
            Dictionary with task information
        """
        # Convert string to TaskPriority enum for in-memory tasks
        task_priority = TaskPriority(priority)

        if persist:
            task = self.task_manager.create_task(
                subject=subject,
                description=description,
                active_form=active_form,
                priority=priority,
            )
        else:
            # Create in-memory task (no persistence)
            import uuid
            from datetime import datetime
            task = Task(
                id=str(uuid.uuid4()),
                subject=subject,
                description=description,
                active_form=active_form,
                priority=task_priority,
            )

        return {
            "id": task.id,
            "subject": task.subject,
            "description": task.description,
            "active_form": task.active_form,
            "status": task.status.value,
            "priority": task.priority.value,
            "created_at": task.created_at.isoformat(),
        }

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a task by ID.

        Args:
            task_id: Unique identifier of the task

        Returns:
            Dictionary with task information, or None if not found
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            return None

        return task.to_dict()

    def update(
        self,
        task_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        description: Optional[str] = None,
        active_form: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update a task.

        Args:
            task_id: Unique identifier of the task
            status: New status if provided
            priority: New priority if provided
            description: New description if provided
            active_form: New active form if provided

        Returns:
            Updated task dictionary, or None if task not found
        """
        task = self.task_manager.update_task(
            task_id=task_id,
            status=status,
            priority=priority,
            description=description,
            active_form=active_form,
        )

        if not task:
            return None

        # Auto-resolve dependencies if task was completed
        if status == "completed":
            unblocked = self.task_manager.resolve_dependencies(task_id)
            if unblocked > 0:
                self.logger.info(
                    f"Resolved {unblocked} dependencies after completing task {task_id}",
                    task_id=task_id,
                    unblocked_count=unblocked
                )

        return task.to_dict()

    def list_all(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all tasks with optional filtering.

        Args:
            status: Filter by status
            priority: Filter by priority
            owner: Filter by owner

        Returns:
            List of task dictionaries
        """
        tasks = self.task_manager.list_tasks(
            status=status,
            priority=priority,
            owner=owner,
            exclude_deleted=True,
        )

        return [task.to_dict() for task in tasks]

    def list_pending(self, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List pending tasks that are not blocked.

        Args:
            owner: Optional filter by owner

        Returns:
            List of pending, unblocked task dictionaries
        """
        tasks = self.task_manager.get_pending_tasks(owner=owner)
        return [task.to_dict() for task in tasks]

    def delete(self, task_id: str) -> bool:
        """
        Delete a task.

        Args:
            task_id: Unique identifier of the task

        Returns:
            True if task was deleted, False otherwise
        """
        return self.task_manager.delete_task(task_id)

    def get_next_pending(self, owner: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get the highest priority pending task.

        Args:
            owner: Optional filter by owner

        Returns:
            Task dictionary, or None if no tasks available
        """
        task = self.task_manager.get_next_pending_task(owner=owner)
        return task.to_dict() if task else None

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all tasks.

        Returns:
            Dictionary with task statistics
        """
        return self.task_manager.get_summary()


# Tool wrappers for agent integration

def task_create(subject: str, description: str, active_form: str = "",
                priority: str = "medium", persist: bool = True) -> Dict[str, Any]:
    """
    Create a new task for tracking work.

    Use this tool when you need to plan or track multiple steps of work.
    Tasks help organize complex workflows into manageable pieces.

    Args:
        subject: Brief title of the task (max 100 chars)
        description: Detailed description of what needs to be done
        active_form: Present continuous form for display (e.g., "Analyzing data")
        priority: Priority level (low, medium, high, critical)
        persist: Whether to persist the task to disk for later recovery

    Returns:
        Dictionary with task ID and details
    """
    # This will be wrapped by the Agent class to use its TodoWrite instance
    raise NotImplementedError("Use Agent.task_create instead")


def task_update(task_id: str, status: Optional[str] = None,
                priority: Optional[str] = None) -> Dict[str, Any]:
    """
    Update an existing task's status or priority.

    Use this tool to mark tasks as completed or change their priority.

    Args:
        task_id: Unique identifier of the task to update
        status: New status (pending, in_progress, completed, failed)
        priority: New priority (low, medium, high, critical)

    Returns:
        Updated task dictionary
    """
    # This will be wrapped by the Agent class to use its TodoWrite instance
    raise NotImplementedError("Use Agent.task_update instead")


def task_list(status: Optional[str] = None, priority: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all tasks with optional filtering.

    Use this tool to see what tasks are currently tracked.

    Args:
        status: Filter by status (pending, in_progress, completed, failed)
        priority: Filter by priority (low, medium, high, critical)

    Returns:
        List of task dictionaries
    """
    # This will be wrapped by the Agent class to use its TodoWrite instance
    raise NotImplementedError("Use Agent.task_list instead")


def task_get(task_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific task.

    Use this tool to get full details including dependencies.

    Args:
        task_id: Unique identifier of the task

    Returns:
        Task dictionary with all details
    """
    # This will be wrapped by the Agent class to use its TodoWrite instance
    raise NotImplementedError("Use Agent.task_get instead")
