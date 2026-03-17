"""
Tool system for BioAgent.

Provides the @tool decorator for marking functions as tools.
"""

import functools
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union, get_type_hints


@dataclass
class ToolInfo:
    """Information about a tool."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema for parameters
    func: Callable
    domain: str = "general"


def tool(func: Optional[Callable] = None, *, domain: str = "general"):
    """
    Decorator to mark a function as a tool.

    Args:
        func: The function to decorate
        domain: The domain category for this tool (e.g., "genetics", "database")

    Example:
        @tool
        def my_function(arg1: str, arg2: int) -> str:
            '''Function description.'''
            return "result"

        @tool(domain="genetics")
        def gene_analysis(gene: str) -> str:
            '''Analyze gene information.'''
            return "analysis"
    """
    def decorator(f: Callable) -> Callable:
        # Extract function metadata
        sig = inspect.signature(f)
        type_hints = get_type_hints(f)

        # Build JSON Schema for parameters
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }

        for name, param in sig.parameters.items():
            if name in ("self", "context"):
                continue

            param_type = type_hints.get(name, "any")

            # Get description from docstring
            description = ""
            if f.__doc__:
                import re
                match = re.search(rf"{name}\s*:\s*([^,\n]+)", f.__doc__)
                if match:
                    description = match.group(1).strip()

            parameters["properties"][name] = {
                "type": _type_to_json_schema(param_type),
                "description": description or f"Parameter {name}"
            }

            # Check if required (no default value)
            if param.default == inspect.Parameter.empty:
                parameters["required"].append(name)

        # Mark the function as a tool
        wrapper = functools.wraps(f)(f)
        wrapper._is_tool = True
        wrapper._tool_info = ToolInfo(
            name=f.__name__,
            description=f.__doc__ or "",
            parameters=parameters,
            func=f,
            domain=domain
        )

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


def _type_to_json_schema(python_type: type) -> str:
    """Convert Python type to JSON Schema type."""
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object"
    }

    # Handle Optional types
    origin = getattr(python_type, "__origin__", None)
    if origin is Union or str(python_type).startswith("typing.Optional"):
        args = getattr(python_type, "__args__", [str])
        return _type_to_json_schema(args[0])

    # Handle List types
    if origin is list:
        return "array"

    return type_map.get(python_type, "string")


def get_tool_info(func: Callable) -> Optional[ToolInfo]:
    """Get ToolInfo from a decorated function."""
    return getattr(func, "_tool_info", None)


def is_tool(func: Callable) -> bool:
    """Check if a function is marked as a tool."""
    return hasattr(func, "_is_tool")
