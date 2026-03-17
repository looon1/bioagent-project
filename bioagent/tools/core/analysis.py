"""
Analysis tools for BioAgent.

Provides code execution capabilities.
"""

import io
import sys
import traceback
from typing import Any, Dict

from bioagent.tools.base import tool


@tool(domain="analysis")
async def run_python_code(
    code: str,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Safely execute Python code and capture output.

    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds

    Returns:
        Dictionary with execution results, output, and any errors
    """
    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()

    result = {
        "success": False,
        "output": "",
        "error": None
    }

    try:
        # Execute the code
        exec_globals = {"__name__": "__main__", "__builtins__": __builtins__}
        exec(code, exec_globals)

        # Get captured output
        output = captured_output.getvalue()
        result["output"] = output
        result["success"] = True

        # Also capture any variables that were defined
        variables = {k: v for k, v in exec_globals.items()
                    if not k.startswith("_") and k not in ("__name__", "__builtins__")}
        if variables:
            result["variables"] = {k: str(v) for k, v in variables.items()}

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        result["error"] = error_msg
        result["traceback"] = traceback.format_exc()

    finally:
        # Restore stdout
        sys.stdout = old_stdout

    return result
