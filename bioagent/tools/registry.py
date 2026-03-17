"""
Tool registry for BioAgent.

Manages tool registration and lookup.
"""

import inspect
from typing import Any, Callable, Dict, List, Optional, Set
import importlib
import pkgutil

from bioagent.tools.base import ToolInfo, is_tool, get_tool_info


class ToolRegistry:
    """Registry for managing available tools."""

    def __init__(self):
        self._tools: Dict[str, ToolInfo] = {}

    def register(self, func: Callable) -> None:
        """
        Register a tool function.

        Args:
            func: A function decorated with @tool
        """
        if not is_tool(func):
            raise ValueError(f"Function {func.__name__} is not marked as a tool")

        info = get_tool_info(func)
        if info:
            self._tools[info.name] = info

    def register_from_module(self, module) -> None:
        """
        Register all tools from a module.

        Args:
            module: Python module to scan for tools
        """
        for name in dir(module):
            obj = getattr(module, name)
            if is_tool(obj):
                self.register(obj)

    def register_from_package(self, package_name: str) -> None:
        """
        Register all tools from a package.

        Args:
            package_name: Package to scan (e.g., "bioagent.tools.core")
        """
        try:
            package = importlib.import_module(package_name)

            # Walk through all modules in the package
            for _, modname, _ in pkgutil.walk_packages(
                path=package.__path__,
                prefix=package.__name__ + "."
            ):
                try:
                    module = importlib.import_module(modname)
                    self.register_from_module(module)
                except Exception as e:
                    # Skip modules that fail to import
                    print(f"Warning: Failed to load module {modname}: {e}")

        except Exception as e:
            print(f"Warning: Failed to load package {package_name}: {e}")

    def get_tool(self, name: str) -> Optional[ToolInfo]:
        """
        Get a tool by name.

        Args:
            name: Name of the tool

        Returns:
            ToolInfo or None if not found
        """
        return self._tools.get(name)

    def list_tools(self, domain: Optional[str] = None) -> List[ToolInfo]:
        """
        List all registered tools.

        Args:
            domain: Optional filter by domain

        Returns:
            List of ToolInfo objects
        """
        tools = list(self._tools.values())
        if domain:
            tools = [t for t in tools if t.domain == domain]
        return tools

    def list_tool_names(self, domain: Optional[str] = None) -> List[str]:
        """
        List all tool names.

        Args:
            domain: Optional filter by domain

        Returns:
            List of tool name strings
        """
        return [t.name for t in self.list_tools(domain)]

    def to_openai_format(self, domain: Optional[str] = None) -> List[Dict]:
        """
        Convert tools to OpenAI function calling format.

        Args:
            domain: Optional filter by domain

        Returns:
            List of tool definitions in OpenAI format
        """
        tools = []
        for tool_info in self.list_tools(domain):
            tools.append({
                "name": tool_info.name,
                "description": tool_info.description,
                "input_schema": tool_info.parameters
            })
        return tools

    async def execute(self, name: str, args: Dict) -> Any:
        """
        Execute a tool by name (supports both sync and async tools).

        Args:
            name: Name of the tool to execute
            args: Arguments to pass to the tool

        Returns:
            Result from the tool function

        Raises:
            ValueError: If tool not found
        """
        tool_info = self.get_tool(name)
        if tool_info is None:
            raise ValueError(f"Tool not found: {name}")

        func = tool_info.func
        if inspect.iscoroutinefunction(func):
            return await func(**args)
        else:
            return func(**args)

    def __len__(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)

    @property
    def tools(self) -> Dict[str, ToolInfo]:
        """
        Get all registered tools (read-only view).

        Returns:
            Dictionary of tool_name -> ToolInfo
        """
        return self._tools.copy()

    @property
    def domains(self) -> Set[str]:
        """
        Get all unique domains from registered tools.

        Returns:
            Set of domain names
        """
        return {tool.domain for tool in self._tools.values()}

    def list_tools_by_domain(self, domain: str) -> List[ToolInfo]:
        """
        List all tools in a specific domain.

        Args:
            domain: Domain name to filter by

        Returns:
            List of ToolInfo objects in the domain
        """
        return [t for t in self._tools.values() if t.domain == domain]
