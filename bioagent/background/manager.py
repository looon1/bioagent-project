"""
Background task manager for BioAgent.

Manages long-running operations that execute asynchronously
without blocking the agent loop.
"""

import asyncio
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

from bioagent.background.capture import (
    _bg_output_buffer,
    _bg_report,
    _install_print_hook,
)
from bioagent.observability import Logger


class BackgroundTaskStatus(str, Enum):
    """Status of a background task."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundTask:
    """
    Represents a background task.

    Attributes:
        task_id: Unique identifier
        tool_name: Name of tool being executed
        tool_call_id: Original LLM tool_call_id
        args: Tool arguments
        status: Current status
        asyncio_task: Reference to asyncio.Task
        created_at: Creation timestamp
        completed_at: Completion timestamp (when done)
        result: Task result (when completed)
        error: Error message (if failed)
        output_lines: Captured stdout output
        source: "explicit" (run_background tool) or "timeout" (promoted from sync)
    """

    task_id: str
    tool_name: str
    tool_call_id: Optional[str]
    args: Dict[str, Any]
    status: BackgroundTaskStatus = BackgroundTaskStatus.RUNNING
    asyncio_task: Optional[asyncio.Task] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    output_lines: List[str] = field(default_factory=list)
    source: str = "explicit"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "args": self.args,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": str(self.result) if self.result else None,
            "error": self.error,
            "output_lines": self.output_lines,
            "source": self.source,
        }


@dataclass
class TaskNotification:
    """Notification for completed background task."""

    task_id: str
    status: BackgroundTaskStatus
    output_lines: List[str]
    result: Optional[Any] = None
    error: Optional[str] = None


class BackgroundTaskManager:
    """
    Manager for background tasks.

    Handles creation, execution, tracking, and cancellation
    of background tasks with output capture and notification support.
    """

    def __init__(
        self, max_retained: int = 50, logger: Optional[Logger] = None
    ):
        """
        Initialize the BackgroundTaskManager.

        Args:
            max_retained: Maximum number of completed tasks to retain
            logger: Optional logger for logging operations
        """
        self.max_retained = max_retained
        self.logger = logger or Logger("background_manager")

        # Task storage
        self._tasks: Dict[str, BackgroundTask] = {}

        # Notification queue (completed tasks)
        self._notifications: Deque[TaskNotification] = deque()

        # Install print hook for output capture
        _install_print_hook()

        self.logger.info(
            f"BackgroundTaskManager initialized",
            max_retained=max_retained
        )

    def start(
        self,
        tool_name: str,
        tool_call_id: Optional[str],
        args: Dict[str, Any],
        coro,
        source: str = "explicit",
    ) -> BackgroundTask:
        """
        Create and start a new background task.

        Args:
            tool_name: Name of tool being executed
            tool_call_id: Original LLM tool_call_id
            args: Tool arguments
            coro: Coroutine to execute
            source: "explicit" or "timeout"

        Returns:
            The created BackgroundTask
        """
        task_id = str(uuid.uuid4())[:8]

        # Create output buffer for this task
        output_buffer: List[str] = []

        async def wrapped():
            """Wrapped coroutine that captures output and handles errors."""
            token = _bg_output_buffer.set(output_buffer)
            try:
                result = await coro
                return result, None, output_buffer
            except Exception as e:
                return None, str(e), output_buffer
            finally:
                _bg_output_buffer.reset(token)

        # Create asyncio task
        asyncio_task = asyncio.create_task(wrapped())

        # Create background task
        bg_task = BackgroundTask(
            task_id=task_id,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            args=args,
            status=BackgroundTaskStatus.RUNNING,
            asyncio_task=asyncio_task,
            source=source,
        )

        # Store task
        self._tasks[task_id] = bg_task

        # Add done callback
        asyncio_task.add_done_callback(
            lambda t: self._on_task_done(task_id, t)
        )

        self.logger.info(
            f"Started background task: {task_id}",
            task_id=task_id,
            tool_name=tool_name,
            source=source,
        )

        # Evict old tasks if needed
        self._evict_old()

        return bg_task

    def adopt(
        self,
        tool_name: str,
        tool_call_id: Optional[str],
        args: Dict[str, Any],
        existing_task: asyncio.Task,
        output_buffer: Optional[List[str]] = None,
    ) -> BackgroundTask:
        """
        Adopt an existing asyncio task as a background task.

        Used when a sync tool execution times out and needs
        to continue in the background.

        Args:
            tool_name: Name of tool being executed
            tool_call_id: Original LLM tool_call_id
            args: Tool arguments
            existing_task: Existing asyncio.Task to adopt
            output_buffer: Existing output buffer (if any)

        Returns:
            The adopted BackgroundTask
        """
        task_id = str(uuid.uuid4())[:8]

        # Create background task
        bg_task = BackgroundTask(
            task_id=task_id,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            args=args,
            status=BackgroundTaskStatus.RUNNING,
            asyncio_task=existing_task,
            source="timeout",
        )

        # Set output buffer if provided
        if output_buffer:
            bg_task.output_lines = output_buffer

        # Store task
        self._tasks[task_id] = bg_task

        # Add done callback
        existing_task.add_done_callback(
            lambda t: self._on_task_done(task_id, t)
        )

        self.logger.info(
            f"Adopted existing task as background: {task_id}",
            task_id=task_id,
            tool_name=tool_name,
        )

        # Evict old tasks if needed
        self._evict_old()

        return bg_task

    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """
        Retrieve a task by ID.

        Args:
            task_id: Unique identifier of the task

        Returns:
            BackgroundTask if found, None otherwise
        """
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[BackgroundTask]:
        """
        Get all tasks.

        Returns:
            List of all BackgroundTask instances
        """
        return list(self._tasks.values())

    def cancel(self, task_id: str) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: Unique identifier of the task

        Returns:
            True if task was cancelled, False otherwise
        """
        task = self._tasks.get(task_id)
        if not task:
            self.logger.warning(
                f"Task not found for cancellation: {task_id}",
                task_id=task_id,
            )
            return False

        if task.status != BackgroundTaskStatus.RUNNING:
            self.logger.warning(
                f"Task not running, cannot cancel: {task_id}",
                task_id=task_id,
                status=task.status.value,
            )
            return False

        # Cancel the asyncio task
        if task.asyncio_task:
            task.asyncio_task.cancel()

        # Update status
        task.status = BackgroundTaskStatus.CANCELLED
        task.completed_at = datetime.now(timezone.utc)

        self.logger.info(
            f"Cancelled background task: {task_id}",
            task_id=task_id,
        )

        return True

    def drain_notifications(self) -> List[TaskNotification]:
        """
        Return all pending notifications and clear the queue.

        Returns:
            List of TaskNotification objects for completed tasks
        """
        notifications = list(self._notifications)
        self._notifications.clear()
        return notifications

    def _on_task_done(
        self, task_id: str, asyncio_task: asyncio.Task
    ) -> None:
        """
        Internal callback for task completion.

        Updates task status and creates notification.

        Args:
            task_id: Unique identifier of the task
            asyncio_task: The completed asyncio.Task
        """
        task = self._tasks.get(task_id)
        if not task:
            self.logger.warning(
                f"Task not found in done callback: {task_id}",
                task_id=task_id,
            )
            return

        # Check if task was cancelled
        if asyncio_task.cancelled():
            task.status = BackgroundTaskStatus.CANCELLED
            task.completed_at = datetime.now(timezone.utc)
            self.logger.info(
                f"Task cancelled: {task_id}",
                task_id=task_id,
            )
            return

        # Get result or error
        try:
            task_result = asyncio_task.result()
            # Handle different return tuple formats:
            # - (result, error, output_buffer) for tasks started via start()
            # - (result, error) for tasks adopted via adopt()
            if len(task_result) == 3:
                result, error, output_buffer = task_result
                # Copy captured output to task
                task.output_lines = output_buffer[:]
            else:
                result, error = task_result
                # Keep existing output_lines (for adopted tasks)

            if error:
                task.status = BackgroundTaskStatus.FAILED
                task.error = error
                self.logger.warning(
                    f"Task failed: {task_id}",
                    task_id=task_id,
                    error=error,
                )
            else:
                task.status = BackgroundTaskStatus.COMPLETED
                task.result = result
                self.logger.info(
                    f"Task completed: {task_id}",
                    task_id=task_id,
                )

            task.completed_at = datetime.now(timezone.utc)

            # Create notification
            notification = TaskNotification(
                task_id=task_id,
                status=task.status,
                output_lines=task.output_lines,
                result=result if not error else None,
                error=error,
            )
            self._notifications.append(notification)

        except Exception as e:
            task.status = BackgroundTaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now(timezone.utc)

            self.logger.error(
                f"Exception in task completion: {task_id}",
                task_id=task_id,
                error=str(e),
            )

            # Create notification for error
            notification = TaskNotification(
                task_id=task_id,
                status=task.status,
                output_lines=task.output_lines,
                error=str(e),
            )
            self._notifications.append(notification)

        # Evict old tasks
        self._evict_old()

    def _evict_old(self) -> None:
        """
        Remove old completed tasks to prevent memory leaks.

        Keeps at most max_retained completed tasks.
        """
        completed_tasks = [
            (task_id, task)
            for task_id, task in self._tasks.items()
            if task.status in (
                BackgroundTaskStatus.COMPLETED,
                BackgroundTaskStatus.FAILED,
                BackgroundTaskStatus.CANCELLED,
            )
        ]

        # Sort by completion time (oldest first)
        completed_tasks.sort(
            key=lambda x: x[1].completed_at or x[1].created_at
        )

        # Evict excess tasks
        evict_count = len(completed_tasks) - self.max_retained
        if evict_count > 0:
            for task_id, _ in completed_tasks[:evict_count]:
                del self._tasks[task_id]

            self.logger.debug(
                f"Evicted {evict_count} old completed tasks",
                evict_count=evict_count,
            )

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all background tasks.

        Returns:
            Dictionary with task statistics
        """
        all_tasks = list(self._tasks.values())

        summary = {
            "total": len(all_tasks),
            "running": sum(
                1 for t in all_tasks if t.status == BackgroundTaskStatus.RUNNING
            ),
            "completed": sum(
                1 for t in all_tasks if t.status == BackgroundTaskStatus.COMPLETED
            ),
            "failed": sum(
                1 for t in all_tasks if t.status == BackgroundTaskStatus.FAILED
            ),
            "cancelled": sum(
                1 for t in all_tasks if t.status == BackgroundTaskStatus.CANCELLED
            ),
            "pending_notifications": len(self._notifications),
        }

        return summary
