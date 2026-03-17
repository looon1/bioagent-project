"""
Compact tool for manual context compression.

Allows the agent to trigger immediate conversation compression
to reduce token usage while preserving important information.
"""

from typing import Dict, Any
from bioagent.tools.base import tool


@tool(domain="context")
async def compact(focus: str = "") -> Dict[str, str]:
    """
    Trigger manual conversation compression.

    Use this when you want to compress the conversation context
    to reduce token usage while preserving important information.

    The compression will:
    1. Save the full conversation to a transcript file
    2. Generate a summary of what has been accomplished
    3. Replace the message history with the summary

    Args:
        focus: Optional focus area to preserve in summary (e.g., "gene analysis",
              "protein structure", "experimental results"). Leave empty for general summary.

    Returns:
        Status message indicating compression was triggered

    Example:
        >>> await compact()
        {'status': 'compression_triggered', 'focus': ''}

        >>> await compact(focus="TP53 gene analysis")
        {'status': 'compression_triggered', 'focus': 'TP53 gene analysis'}
    """
    return {
        "status": "compression_triggered",
        "focus": focus
    }
