"""
WorktreeManager for git worktree management and task binding.

Provides file-based persistence for worktrees with JSON backing,
and manages task-worktree binding relationships.
"""

import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from bioagent.observability import Logger
from bioagent.worktree.models import Worktree, WorktreeStatus


class EventBus:
    """
    Event bus for logging worktree lifecycle events.

    Events are appended to a JSONL file for observability.
    """

    def __init__(self, event_log_path: Path, logger: Optional[Logger] = None):
        """
        Initialize EventBus.

        Args:
            event_log_path: Path to event log file (JSONL format)
            logger: Optional logger for logging operations
        """
        self.path = Path(event_log_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logger or Logger("worktree_events")

        if not self.path.exists():
            self.path.write_text("")

        self.logger.debug(f"EventBus initialized at {self.path}")

    def emit(
        self,
        event: str,
        task: Optional[Dict[str, Any]] = None,
        worktree: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Emit an event to the event log.

        Args:
            event: Event name/type
            task: Optional task information
            worktree: Optional worktree information
            error: Optional error information
        """
        payload = {
            "event": event,
            "ts": time.time(),
            "task": task or {},
            "worktree": worktree or {},
        }
        if error:
            payload["error"] = error

        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")

        self.logger.debug(f"Emitted event: {event}")

    def list_recent(self, limit: int = 20) -> str:
        """
        List recent events from the event log.

        Args:
            limit: Maximum number of events to return

        Returns:
            JSON string of recent events
        """
        n = max(1, min(int(limit or 20), 200))
        lines = self.path.read_text(encoding="utf-8").splitlines()
        recent = lines[-n:] if lines else []

        items = []
        for line in recent:
            try:
                items.append(json.loads(line))
            except Exception:
                items.append({"event": "parse_error", "raw": line})

        return json.dumps(items, indent=2)

    def clear(self) -> None:
        """Clear all events from the log."""
        self.path.write_text("")
        self.logger.debug("Event log cleared")


class WorktreeManager:
    """
    Manages git worktrees with task binding support.

    Provides:
    - Git worktree creation, listing, status, removal
    - Task-worktree binding and automatic task status updates
    - Event logging for lifecycle tracking
    """

    def __init__(
        self,
        repo_root: Path,
        tasks_dir: Path,
        worktrees_dir: Path,
        logger: Optional[Logger] = None,
    ):
        """
        Initialize WorktreeManager.

        Args:
            repo_root: Path to git repository root
            tasks_dir: Path to tasks directory (for task binding)
            worktrees_dir: Path to worktrees directory
            logger: Optional logger for logging operations
        """
        self.repo_root = Path(repo_root)
        self.tasks_dir = Path(tasks_dir)
        self.worktrees_dir = Path(worktrees_dir)
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger or Logger("worktree_manager")

        # Initialize event bus
        self.events = EventBus(
            self.worktrees_dir / "events.jsonl",
            self.logger
        )

        # Index file for worktree tracking
        self.index_path = self.worktrees_dir / "index.json"
        if not self.index_path.exists():
            self._save_index({"worktrees": []})

        # Check if we're in a git repository
        self.git_available = self._is_git_repo()

        self.logger.info(
            f"WorktreeManager initialized",
            repo_root=str(self.repo_root),
            worktrees_dir=str(self.worktrees_dir),
            git_available=self.git_available
        )

    def _is_git_repo(self) -> bool:
        """Check if repo_root is inside a git repository."""
        try:
            r = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return r.returncode == 0
        except Exception:
            return False

    def _run_git(self, args: List[str], cwd: Optional[Path] = None) -> str:
        """
        Run a git command and return output.

        Args:
            args: List of git arguments
            cwd: Optional working directory (defaults to repo_root)

        Returns:
            Command output (stdout + stderr)

        Raises:
            RuntimeError: If git command fails
        """
        if not self.git_available:
            raise RuntimeError("Not in a git repository. worktree tools require git.")

        work_cwd = cwd or self.repo_root
        r = subprocess.run(
            ["git", *args],
            cwd=work_cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r.returncode != 0:
            msg = (r.stdout + r.stderr).strip()
            raise RuntimeError(msg or f"git {' '.join(args)} failed")
        return (r.stdout + r.stderr).strip() or "(no output)"

    def _load_index(self) -> Dict[str, Any]:
        """Load worktree index from disk."""
        return json.loads(self.index_path.read_text())

    def _save_index(self, data: Dict[str, Any]) -> None:
        """Save worktree index to disk."""
        self.index_path.write_text(json.dumps(data, indent=2))

    def _find_by_name(self, name: str) -> Optional[Worktree]:
        """Find a worktree by name."""
        idx = self._load_index()
        for wt_data in idx.get("worktrees", []):
            if wt_data.get("name") == name:
                return Worktree.from_dict(wt_data)
        return None

    def _find_by_task_id(self, task_id: str) -> Optional[Worktree]:
        """Find a worktree by bound task ID."""
        idx = self._load_index()
        for wt_data in idx.get("worktrees", []):
            if wt_data.get("task_id") == task_id:
                return Worktree.from_dict(wt_data)
        return None

    def _validate_name(self, name: str) -> None:
        """
        Validate worktree name.

        Args:
            name: Name to validate

        Raises:
            ValueError: If name is invalid
        """
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,40}", name or ""):
            raise ValueError(
                "Invalid worktree name. Use 1-40 chars: letters, numbers, ., _, -"
            )

    def create(
        self,
        name: str,
        task_id: Optional[str] = None,
        base_ref: str = "HEAD"
    ) -> Dict[str, Any]:
        """
        Create a new git worktree and optionally bind to a task.

        Args:
            name: Worktree name
            task_id: Optional task ID to bind to
            base_ref: Git reference to create worktree from (default: HEAD)

        Returns:
            Dictionary with worktree information

        Raises:
            ValueError: If worktree already exists or validation fails
            RuntimeError: If git command fails
        """
        self._validate_name(name)

        if self._find_by_name(name):
            raise ValueError(f"Worktree '{name}' already exists in index")

        # Verify task exists if provided
        if task_id is not None:
            task_file = self.tasks_dir / f"{task_id}.json"
            if not task_file.exists():
                raise ValueError(f"Task {task_id} not found")

        path = self.worktrees_dir / name
        branch = f"wt/{name}"

        self.events.emit(
            "worktree.create.before",
            task={"id": task_id} if task_id is not None else {},
            worktree={"name": name, "base_ref": base_ref},
        )

        try:
            # Create git worktree
            self._run_git(["worktree", "add", "-b", branch, str(path), base_ref])

            # Create worktree entry
            worktree = Worktree(
                name=name,
                path=path,
                branch=branch,
                task_id=task_id,
                status=WorktreeStatus.ACTIVE,
                base_ref=base_ref,
            )

            # Update index
            idx = self._load_index()
            idx["worktrees"].append(worktree.to_dict())
            self._save_index(idx)

            # Bind to task if provided
            if task_id is not None:
                self._bind_task(task_id, name)

            self.events.emit(
                "worktree.create.after",
                task={"id": task_id} if task_id is not None else {},
                worktree=worktree.to_dict(),
            )

            self.logger.info(
                f"Created worktree '{name}'",
                worktree_name=name,
                task_id=task_id,
                branch=branch,
            )

            return worktree.to_dict()

        except Exception as e:
            self.events.emit(
                "worktree.create.failed",
                task={"id": task_id} if task_id is not None else {},
                worktree={"name": name, "base_ref": base_ref},
                error=str(e),
            )
            raise

    def list_all(self) -> List[Dict[str, Any]]:
        """
        List all worktrees.

        Returns:
            List of worktree dictionaries
        """
        idx = self._load_index()
        wts = idx.get("worktrees", [])
        return wts

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a worktree by name.

        Args:
            name: Worktree name

        Returns:
            Worktree dictionary if found, None otherwise
        """
        wt = self._find_by_name(name)
        return wt.to_dict() if wt else None

    def status(self, name: str) -> str:
        """
        Show git status for a worktree.

        Args:
            name: Worktree name

        Returns:
            Git status output
        """
        wt = self._find_by_name(name)
        if not wt:
            return f"Error: Unknown worktree '{name}'"

        if not wt.path.exists():
            return f"Error: Worktree path missing: {wt.path}"

        try:
            r = subprocess.run(
                ["git", "status", "--short", "--branch"],
                cwd=wt.path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            text = (r.stdout + r.stderr).strip()
            return text or "Clean worktree"
        except Exception as e:
            return f"Error: {e}"

    def run(
        self,
        name: str,
        command: str,
        timeout: int = 300
    ) -> str:
        """
        Run a shell command in a worktree directory.

        Args:
            name: Worktree name
            command: Shell command to execute
            timeout: Command timeout in seconds

        Returns:
            Command output

        Raises:
            ValueError: If worktree not found or command is dangerous
        """
        # Block dangerous commands
        dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
        if any(d in command for d in dangerous):
            raise ValueError("Dangerous command blocked")

        wt = self._find_by_name(name)
        if not wt:
            return f"Error: Unknown worktree '{name}'"

        if not wt.path.exists():
            return f"Error: Worktree path missing: {wt.path}"

        try:
            r = subprocess.run(
                command,
                shell=True,
                cwd=wt.path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            out = (r.stdout + r.stderr).strip()
            return out[:50000] if out else "(no output)"
        except subprocess.TimeoutExpired:
            return f"Error: Timeout ({timeout}s)"
        except Exception as e:
            return f"Error: {e}"

    def remove(
        self,
        name: str,
        force: bool = False,
        complete_task: bool = False
    ) -> str:
        """
        Remove a worktree and optionally complete its bound task.

        Args:
            name: Worktree name
            force: Force removal even if worktree has changes
            complete_task: If True, mark bound task as completed

        Returns:
            Status message

        Raises:
            ValueError: If worktree not found
            RuntimeError: If git command fails
        """
        wt = self._find_by_name(name)
        if not wt:
            raise ValueError(f"Unknown worktree '{name}'")

        self.events.emit(
            "worktree.remove.before",
            task={"id": wt.task_id} if wt.task_id is not None else {},
            worktree={"name": name, "path": str(wt.path)},
        )

        try:
            # Remove git worktree
            args = ["worktree", "remove"]
            if force:
                args.append("--force")
            args.append(str(wt.path))
            self._run_git(args)

            # Complete task if requested and task is bound
            if complete_task and wt.task_id is not None:
                self._complete_task(wt.task_id, name)

            # Update index
            idx = self._load_index()
            for item in idx.get("worktrees", []):
                if item.get("name") == name:
                    item["status"] = "removed"
                    item["removed_at"] = datetime.now().isoformat()
                    # Unbind from task
                    if item.get("task_id"):
                        self._unbind_task(item["task_id"])
            self._save_index(idx)

            self.events.emit(
                "worktree.remove.after",
                task={"id": wt.task_id} if wt.task_id is not None else {},
                worktree={
                    "name": name,
                    "path": str(wt.path),
                    "status": "removed"
                },
            )

            self.logger.info(
                f"Removed worktree '{name}'",
                worktree_name=name,
                task_completed=complete_task,
            )

            return f"Removed worktree '{name}'"

        except Exception as e:
            self.events.emit(
                "worktree.remove.failed",
                task={"id": wt.task_id} if wt.task_id is not None else {},
                worktree={"name": name, "path": str(wt.path)},
                error=str(e),
            )
            raise

    def keep(self, name: str) -> Dict[str, Any]:
        """
        Mark a worktree as kept (without removing).

        Args:
            name: Worktree name

        Returns:
            Updated worktree dictionary

        Raises:
            ValueError: If worktree not found
        """
        wt = self._find_by_name(name)
        if not wt:
            raise ValueError(f"Unknown worktree '{name}'")

        # Update index
        idx = self._load_index()
        kept = None
        for item in idx.get("worktrees", []):
            if item.get("name") == name:
                item["status"] = "kept"
                item["kept_at"] = datetime.now().isoformat()
                kept = item
        self._save_index(idx)

        self.events.emit(
            "worktree.keep",
            task={"id": wt.task_id} if wt.task_id is not None else {},
            worktree=kept,
        )

        self.logger.info(f"Marked worktree '{name}' as kept", worktree_name=name)

        return kept

    def _bind_task(self, task_id: str, worktree_name: str) -> None:
        """
        Bind a task to a worktree.

        Updates task status to in_progress if pending.

        Args:
            task_id: Task ID to bind
            worktree_name: Worktree name to bind to
        """
        task_file = self.tasks_dir / f"{task_id}.json"
        if not task_file.exists():
            self.logger.warning(f"Task {task_id} not found for binding")
            return

        with open(task_file, "r") as f:
            task = json.load(f)

        task["worktree"] = worktree_name
        if task.get("status") == "pending":
            task["status"] = "in_progress"
        task["updated_at"] = datetime.now().isoformat()

        with open(task_file, "w") as f:
            json.dump(task, f, indent=2)

        self.logger.debug(
            f"Bound task {task_id} to worktree '{worktree_name}'",
            task_id=task_id,
            worktree_name=worktree_name
        )

    def _unbind_task(self, task_id: str) -> None:
        """
        Unbind a task from its worktree.

        Args:
            task_id: Task ID to unbind
        """
        task_file = self.tasks_dir / f"{task_id}.json"
        if not task_file.exists():
            return

        with open(task_file, "r") as f:
            task = json.load(f)

        task["worktree"] = ""
        task["updated_at"] = datetime.now().isoformat()

        with open(task_file, "w") as f:
            json.dump(task, f, indent=2)

        self.logger.debug(f"Unbound task {task_id} from worktree", task_id=task_id)

    def _complete_task(self, task_id: str, worktree_name: str) -> None:
        """
        Mark a task as completed after worktree removal.

        Args:
            task_id: Task ID to complete
            worktree_name: Worktree name that completed the task
        """
        task_file = self.tasks_dir / f"{task_id}.json"
        if not task_file.exists():
            return

        with open(task_file, "r") as f:
            task = json.load(f)

        before_status = task.get("status", "")
        task["status"] = "completed"
        task["worktree"] = ""
        task["updated_at"] = datetime.now().isoformat()

        if task.get("completed_at") is None:
            task["completed_at"] = datetime.now().isoformat()

        with open(task_file, "w") as f:
            json.dump(task, f, indent=2)

        # Emit task completion event
        self.events.emit(
            "task.completed",
            task={
                "id": task_id,
                "subject": task.get("subject", ""),
                "status": "completed",
                "previous_status": before_status,
            },
            worktree={"name": worktree_name},
        )

        self.logger.info(
            f"Completed task {task_id}",
            task_id=task_id,
            worktree_name=worktree_name
        )

    def list_events(self, limit: int = 20) -> str:
        """
        List recent worktree lifecycle events.

        Args:
            limit: Maximum number of events to return

        Returns:
            JSON string of recent events
        """
        return self.events.list_recent(limit)

    def cleanup_removed(self, days: int = 7) -> int:
        """
        Clean up removed worktrees from index after retention period.

        Args:
            days: Number of days to retain removed worktrees

        Returns:
            Number of worktrees cleaned up
        """
        import time as time_module
        cutoff = time_module.time() - (days * 86400)

        idx = self._load_index()
        original_count = len(idx.get("worktrees", []))

        # Filter out old removed worktrees
        idx["worktrees"] = [
            wt for wt in idx.get("worktrees", [])
            if not (
                wt.get("status") == "removed"
                and wt.get("removed_at")
                and datetime.fromisoformat(wt["removed_at"]).timestamp() < cutoff
            )
        ]

        removed_count = original_count - len(idx["worktrees"])
        self._save_index(idx)

        if removed_count > 0:
            self.logger.info(
                f"Cleaned up {removed_count} old removed worktrees",
                days=days,
                removed_count=removed_count
            )

        return removed_count

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all worktrees.

        Returns:
            Dictionary with worktree statistics
        """
        idx = self._load_index()
        wts = idx.get("worktrees", [])

        summary = {
            "total": len(wts),
            "active": sum(1 for wt in wts if wt.get("status") == "active"),
            "removed": sum(1 for wt in wts if wt.get("status") == "removed"),
            "kept": sum(1 for wt in wts if wt.get("status") == "kept"),
            "with_task": sum(1 for wt in wts if wt.get("task_id")),
        }

        return summary
