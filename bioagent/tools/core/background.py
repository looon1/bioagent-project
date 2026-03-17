"""
Background task tools for BioAgent.

Tools for running, checking, and canceling background tasks.
"""

from typing import Any, Dict, List, Optional

# These tools are registered dynamically by Agent._register_background_tools()
# They are registered directly to avoid circular import issues.


def run_background(
    tool_name: str,
    tool_args: Dict[str, Any],
    agent_context: Any,
) -> Dict[str, Any]:
    """
    Run a tool in the background.

    Use this when you need to run a long-running operation
    without blocking the agent's main execution loop.

    Args:
        tool_name: Name of the tool to run in background
        tool_args: Arguments to pass to the tool (as a dictionary)
        agent_context: Agent context (injected by registration)

    Returns:
        Dictionary with task_id and status information
    """
    bg_manager = getattr(agent_context, "bg_manager", None)
    if not bg_manager:
        return {"error": "Background task system is not enabled"}

    # Get the tool from registry
    tool_registry = getattr(agent_context, "tool_registry", None)
    if not tool_registry:
        return {"error": "Tool registry not available"}

    # Check if tool exists
    tool_func = tool_registry.get_tool(tool_name)
    if not tool_func:
        return {"error": f"Tool '{tool_name}' not found"}

    # Execute the tool in background
    import asyncio

    async def run_tool():
        return await tool_registry.execute(tool_name, tool_args)

    bg_task = bg_manager.start(
        tool_name=tool_name,
        tool_call_id=None,
        args=tool_args,
        coro=run_tool(),
        source="explicit",
    )

    return {
        "task_id": bg_task.task_id,
        "status": bg_task.status.value,
        "tool_name": bg_task.tool_name,
        "message": f"Background task {bg_task.task_id} started",
    }


def check_background(
    task_id: Optional[str],
    agent_context: Any,
) -> Dict[str, Any]:
    """
    Check the status of background tasks.

    Use this to see the progress of running background tasks.

    Args:
        task_id: Optional task ID to check. If None, returns all tasks.
        agent_context: Agent context (injected by registration)

    Returns:
        Dictionary with task status information or list of all tasks
    """
    bg_manager = getattr(agent_context, "bg_manager", None)
    if not bg_manager:
        return {"error": "Background task system is not enabled"}

    if task_id:
        # Check specific task
        task = bg_manager.get_task(task_id)
        if not task:
            return {"error": f"Task {task_id} not found"}

        return task.to_dict()
    else:
        # Return all tasks
        tasks = bg_manager.get_all_tasks()
        return {
            "tasks": [task.to_dict() for task in tasks],
            "summary": bg_manager.get_summary(),
        }


def cancel_background(
    task_id: str,
    agent_context: Any,
) -> Dict[str, Any]:
    """
    Cancel a running background task.

    Use this to stop a background task that is no longer needed.

    Args:
        task_id: ID of the task to cancel
        agent_context: Agent context (injected by registration)

    Returns:
        Dictionary with cancellation status
    """
    bg_manager = getattr(agent_context, "bg_manager", None)
    if not bg_manager:
        return {"error": "Background task system is not enabled"}

    success = bg_manager.cancel(task_id)

    if success:
        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": f"Task {task_id} has been cancelled",
        }
    else:
        return {
            "task_id": task_id,
            "status": "failed",
            "error": f"Failed to cancel task {task_id} - task may not exist or not be running",
        }
