"""
Kanban Board for visual task management.

Provides a text-based Kanban board for tracking tasks across
different states: pending, in_progress, completed, blocked.
"""

from typing import Dict, List, Optional

from bioagent.tasks.manager import TaskManager


class KanbanBoard:
    """
    Text-based Kanban board for task visualization.

    Displays tasks in columns representing their status.
    """

    def __init__(
        self, task_manager: TaskManager, max_width: int = 80
    ):
        """
        Initialize Kanban board.

        Args:
            task_manager: Task manager for fetching tasks
            max_width: Maximum width for board display
        """
        self.task_manager = task_manager
        self.max_width = max_width

        # Column configurations
        self.columns = {
            "pending": {
                "marker": "[ ]",
                "label": "PENDING",
                "width": max_width // 4,
            },
            "in_progress": {
                "marker": "[>]",
                "label": "IN PROGRESS",
                "width": max_width // 4,
            },
            "completed": {
                "marker": "[x]",
                "label": "COMPLETED",
                "width": max_width // 4,
            },
            "blocked": {
                "marker": "[/]",
                "label": "BLOCKED",
                "width": max_width // 4,
            },
        }

    def display(
        self,
        owner: Optional[str] = None,
        limit: Optional[int] = None,
        show_empty: bool = True,
    ) -> str:
        """
        Generate a Kanban board display.

        Args:
            owner: Filter tasks by owner (None = all)
            limit: Max tasks per column
            show_empty: Whether to show empty columns

        Returns:
            Formatted Kanban board as string
        """
        # Get all tasks
        all_tasks = []
        for status in self.columns:
            tasks = self.task_manager.list_tasks(status=status, owner=owner)
            if limit:
                tasks = tasks[:limit]
            all_tasks.extend(tasks)

        # Build columns
        column_outputs = []
        for status, config in self.columns.items():
            tasks = [t for t in all_tasks if t.status.value == status]

            if not tasks and not show_empty:
                continue

            # Column header
            header = f"\n{config['label']} ({len(tasks)})"
            separator = "=" * len(config["label"])

            # Task items
            items = []
            for task in tasks:
                task_id = task.id[:8]
                subject = task.subject or "No subject"
                task_owner = task.owner or ""
                priority = task.priority.value if task.priority else "medium"

                # Build task line
                owner_mark = f" @{task_owner}" if task_owner else ""
                priority_mark = {
                    "critical": "!",
                    "high": "*",
                    "medium": "",
                    "low": "-",
                }.get(priority, "")

                line = f"{config['marker']} #{task_id}: {subject[:30]}{owner_mark}{priority_mark}"
                items.append(line)

            # Combine column
            column = f"{separator}\n{header}\n{separator}\n"
            if items:
                column += "\n".join(items)
            else:
                column += "  (empty)"

            column_outputs.append(column)

        # Board border
        border = "=" * self.max_width

        # Combine all columns
        board = f"\n{border}\n"
        board += "KANBAN BOARD"
        if owner:
            board += f" (filter: {owner})"
        board += f"\n{border}"
        board += "\n".join(column_outputs)
        board += f"\n{border}\n"

        return board

    def get_summary(self, owner: Optional[str] = None) -> Dict[str, int]:
        """
        Get task summary by status.

        Args:
            owner: Filter by owner (None = all)

        Returns:
            Dictionary with counts per status
        """
        summary = {status: 0 for status in self.columns}

        for status in self.columns:
            tasks = self.task_manager.list_tasks(status=status, owner=owner)
            summary[status] = len(tasks)

        return summary

    def get_priority_summary(self, owner: Optional[str] = None) -> Dict[str, int]:
        """
        Get task summary by priority.

        Args:
            owner: Filter by owner (None = all)

        Returns:
            Dictionary with counts per priority
        """
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        for status in self.columns:
            tasks = self.task_manager.list_tasks(status=status, owner=owner)
            for task in tasks:
                priority = task.priority.value if task.priority else "medium"
                if priority in summary:
                    summary[priority] += 1

        return summary

    def get_blocked_tasks(self, owner: Optional[str] = None) -> List:
        """
        Get all blocked tasks.

        Args:
            owner: Filter by owner (None = all)

        Returns:
            List of blocked tasks
        """
        return self.task_manager.list_tasks(status="blocked", owner=owner)

    def get_overdue_tasks(self, owner: Optional[str] = None) -> List:
        """
        Get tasks that have been in progress too long.

        Args:
            owner: Filter by owner (None = all)

        Returns:
            List of overdue tasks
        """
        # Get all in_progress tasks
        tasks = self.task_manager.list_tasks(status="in_progress", owner=owner)

        # In a real implementation, we'd check task timestamps
        # For now, return all in_progress tasks
        return tasks

    def format_task_summary(
        self, owner: Optional[str] = None
    ) -> str:
        """
        Generate a compact task summary.

        Args:
            owner: Filter by owner (None = all)

        Returns:
            Formatted summary string
        """
        status_summary = self.get_summary(owner)
        priority_summary = self.get_priority_summary(owner)

        lines = ["\n=== Task Summary ==="]
        lines.append(f"By Status:")
        for status, count in status_summary.items():
            marker = self.columns[status]["marker"]
            lines.append(f"  {marker} {status}: {count}")

        lines.append(f"\nBy Priority:")
        for priority, count in priority_summary.items():
            marker = {
                "critical": "!",
                "high": "*",
                "medium": "",
                "low": "-",
            }.get(priority, "")
            lines.append(f"  {priority}{marker}: {count}")

        # Blocked tasks
        blocked = self.get_blocked_tasks(owner)
        if blocked:
            lines.append(f"\nBlocked Tasks ({len(blocked)}):")
            for task in blocked[:5]:  # Show first 5
                task_id = task.id[:8]
                subject = task.subject or "No subject"
                lines.append(f"  #{task_id}: {subject[:50]}")
            if len(blocked) > 5:
                lines.append(f"  ... and {len(blocked) - 5} more")

        return "\n".join(lines)


class SprintKanban(KanbanBoard):
    """
    Kanban board with sprint planning support.

    Tracks tasks within a sprint context.
    """

    def __init__(
        self,
        task_manager: TaskManager,
        sprint_name: str = "current",
        sprint_length: int = 7,
    ):
        """
        Initialize sprint Kanban board.

        Args:
            task_manager: Task manager
            sprint_name: Name of current sprint
            sprint_length: Length of sprint in days
        """
        super().__init__(task_manager)
        self.sprint_name = sprint_name
        self.sprint_length = sprint_length
        self.sprint_tasks: List[str] = []

    def add_to_sprint(self, task_id: str) -> None:
        """
        Add a task to the current sprint.

        Args:
            task_id: Task ID to add
        """
        if task_id not in self.sprint_tasks:
            self.sprint_tasks.append(task_id)

    def remove_from_sprint(self, task_id: str) -> None:
        """
        Remove a task from the sprint.

        Args:
            task_id: Task ID to remove
        """
        if task_id in self.sprint_tasks:
            self.sprint_tasks.remove(task_id)

    def display_sprint(self) -> str:
        """
        Display the sprint board.

        Returns:
            Formatted sprint board string
        """
        board = self.display()
        sprint_info = f"\n=== Sprint: {self.sprint_name} ({self.sprint_length} days) ==="
        sprint_info += f"\nTasks in sprint: {len(self.sprint_tasks)}"

        return sprint_info + "\n" + board

    def get_sprint_progress(self) -> Dict[str, int]:
        """
        Get sprint progress metrics.

        Returns:
            Dictionary with progress metrics
        """
        completed = 0
        total = len(self.sprint_tasks)

        for task_id in self.sprint_tasks:
            task = self.task_manager.get(task_id)
            if task and task.status.value == "completed":
                completed += 1

        return {
            "total": total,
            "completed": completed,
            "remaining": total - completed,
            "progress_percent": (completed / total * 100) if total > 0 else 0,
        }
