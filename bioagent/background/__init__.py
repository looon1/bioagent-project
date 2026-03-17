"""
Background task system for BioAgent.

Provides support for long-running operations that execute
asynchronously without blocking the agent loop.
"""

from bioagent.background.manager import (
    BackgroundTask,
    BackgroundTaskStatus,
    BackgroundTaskManager,
)

__all__ = [
    "BackgroundTask",
    "BackgroundTaskStatus",
    "BackgroundTaskManager",
]
