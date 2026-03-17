"""
Output capture mechanism for background tasks.

Captures stdout output from running tasks for progress reporting.
"""

import builtins
from contextvars import ContextVar
from typing import List, Optional

# ContextVar for per-task output capture
_bg_output_buffer: ContextVar[Optional[List[str]]] = ContextVar(
    "_bg_output_buffer", default=None
)

_original_print: Optional[object] = None
_print_hook_installed: bool = False


def _bg_aware_print(*args, **kwargs) -> None:
    """
    Print hook that captures output to background task buffer.

    If a background task context is active, captures the output.
    Always forwards to the original print function.
    """
    # Check if we're in a background task context and not writing to a specific file
    buffer = _bg_output_buffer.get()
    if buffer is not None and "file" not in kwargs:
        # Capture the output to buffer
        import io
        s = io.StringIO()
        kwargs_copy = kwargs.copy()
        kwargs_copy["file"] = s
        _original_print(*args, **kwargs_copy)
        buffer.append(s.getvalue().rstrip("\n"))

    # Always call the original print
    _original_print(*args, **kwargs)


def _install_print_hook() -> None:
    """
    Install the print hook for output capture.

    This is idempotent - multiple calls will not reinstall the hook.
    """
    global _original_print, _print_hook_installed

    if _print_hook_installed:
        return

    _original_print = builtins.print
    builtins.print = _bg_aware_print
    _print_hook_installed = True


def _bg_report(message: str) -> None:
    """
    Helper to report progress to the background task output buffer.

    Args:
        message: Progress message to capture
    """
    buffer = _bg_output_buffer.get()
    if buffer is not None:
        buffer.append(message)
