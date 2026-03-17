"""
Worktree tools for BioAgent.

Provides git worktree management tools for parallel task execution.
"""

from typing import Any, Dict, Optional
from bioagent.tools.base import tool


@tool(domain="worktree")
async def worktree_create(
    name: str,
    task_id: Optional[str] = None,
    base_ref: str = "HEAD"
) -> Dict[str, Any]:
    """
    Create a new git worktree and optionally bind it to a task.

    Worktrees provide isolated directories for parallel task execution.
    Use worktrees when working on multiple tasks simultaneously to avoid conflicts.

    Args:
        name: Worktree name (1-40 chars: letters, numbers, ., _, -)
        task_id: Optional task ID to bind the worktree to (auto-advances task to in_progress)
        base_ref: Git reference to create worktree from (default: HEAD)

    Returns:
        Dictionary with worktree information including name, path, branch, status

    Example:
        worktree_create(name="auth-refactor", task_id="abc123")
        # Creates .worktrees/auth-refactor/ on branch wt/auth-refactor
        # Binds task abc123 to this worktree and advances it to in_progress
    """
    # This will be wrapped by Agent class to use its WorktreeManager instance
    raise NotImplementedError("Use Agent.worktree_create instead")


@tool(domain="worktree")
async def worktree_list() -> Dict[str, Any]:
    """
    List all worktrees tracked in the index.

    Use this to see what worktrees exist and their status.

    Returns:
        Dictionary with list of worktrees and their details

    Example:
        worktree_list()
        # Returns: {
        #   "worktrees": [
        #     {"name": "auth-refactor", "status": "active", "branch": "wt/auth-refactor", ...},
        #     {"name": "ui-login", "status": "kept", "branch": "wt/ui-login", ...}
        #   ]
        # }
    """
    # This will be wrapped by Agent class to use its WorktreeManager instance
    raise NotImplementedError("Use Agent.worktree_list instead")


@tool(domain="worktree")
async def worktree_get(name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific worktree.

    Args:
        name: Worktree name

    Returns:
        Worktree dictionary with full details or error if not found

    Example:
        worktree_get(name="auth-refactor")
        # Returns: {"name": "auth-refactor", "path": "...", "branch": "...", ...}
    """
    # This will be wrapped by Agent class to use its WorktreeManager instance
    raise NotImplementedError("Use Agent.worktree_get instead")


@tool(domain="worktree")
async def worktree_status(name: str) -> str:
    """
    Show git status for a worktree.

    Use this to check what changes exist in a worktree.

    Args:
        name: Worktree name

    Returns:
        Git status output showing modified/added/deleted files

    Example:
        worktree_status(name="auth-refactor")
        # Returns: "## wt/auth-refactor\n M config.py\n?? new_file.py"
    """
    # This will be wrapped by Agent class to use its WorktreeManager instance
    raise NotImplementedError("Use Agent.worktree_status instead")


@tool(domain="worktree")
async def worktree_run(
    name: str,
    command: str,
    timeout: int = 300
) -> str:
    """
    Run a shell command in a worktree directory.

    Use this to execute commands within an isolated worktree context.

    Args:
        name: Worktree name to run command in
        command: Shell command to execute (e.g., "python script.py", "git status")
        timeout: Command timeout in seconds (default: 300)

    Returns:
        Command output (stdout + stderr), or error message

    Example:
        worktree_run(name="auth-refactor", command="python test.py")
        # Runs "python test.py" in the auth-refactor worktree directory
        # Returns the test output
    """
    # This will be wrapped by Agent class to use its WorktreeManager instance
    raise NotImplementedError("Use Agent.worktree_run instead")


@tool(domain="worktree")
async def worktree_remove(
    name: str,
    force: bool = False,
    complete_task: bool = False
) -> str:
    """
    Remove a worktree and optionally complete its bound task.

    Use this to clean up a worktree after work is done.
    Setting complete_task=True will also mark the bound task as completed.

    Args:
        name: Worktree name to remove
        force: Force removal even if worktree has uncommitted changes
        complete_task: If True, mark the bound task as completed

    Returns:
        Status message confirming removal

    Example:
        worktree_remove(name="auth-refactor", complete_task=True)
        # Removes the auth-refactor worktree and marks its bound task as completed
    """
    # This will be wrapped by Agent class to use its WorktreeManager instance
    raise NotImplementedError("Use Agent.worktree_remove instead")


@tool(domain="worktree")
async def worktree_keep(name: str) -> Dict[str, Any]:
    """
    Mark a worktree as kept without removing it.

    Use this to preserve a worktree for later use (e.g., for code review).

    Args:
        name: Worktree name to keep

    Returns:
        Updated worktree dictionary with status="kept"

    Example:
        worktree_keep(name="ui-login")
        # Marks the ui-login worktree as kept for later reference
    """
    # This will be wrapped by Agent class to use its WorktreeManager instance
    raise NotImplementedError("Use Agent.worktree_keep instead")


@tool(domain="worktree")
async def worktree_events(limit: int = 20) -> str:
    """
    List recent worktree lifecycle events.

    Use this to see the history of worktree and task operations.

    Args:
        limit: Maximum number of events to return (default: 20, max: 200)

    Returns:
        JSON string of recent events

    Example:
        worktree_events(limit=10)
        # Returns JSON array of events like:
        # [{"event": "worktree.create.after", "worktree": {...}, "ts": 1234567890}]
    """
    # This will be wrapped by Agent class to use its WorktreeManager instance
    raise NotImplementedError("Use Agent.worktree_events instead")


@tool(domain="worktree")
async def worktree_summary() -> Dict[str, Any]:
    """
    Get a summary of all worktrees.

    Use this to quickly see worktree statistics.

    Returns:
        Dictionary with worktree counts by status

    Example:
        worktree_summary()
        # Returns: {"total": 5, "active": 3, "removed": 1, "kept": 1, "with_task": 3}
    """
    # This will be wrapped by Agent class to use its WorktreeManager instance
    raise NotImplementedError("Use Agent.worktree_summary instead")
