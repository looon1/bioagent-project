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
        self._disabled_domains: Set[str] = set()
        self._disabled_tools: Set[str] = set()

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
        tools = []
        for tool in self._tools.values():
            # Skip disabled tools
            if tool.name in self._disabled_tools:
                continue

            # Filter by domain if specified
            if domain:
                if tool.domain == domain:
                    tools.append(tool)
            else:
                tools.append(tool)
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

    def enable_domain(self, domain: str) -> int:
        """
        Enable all tools in a domain.

        Args:
            domain: Domain name to enable

        Returns:
            Number of tools enabled
        """
        if domain in self._disabled_domains:
            self._disabled_domains.remove(domain)
            # Re-enable tools in this domain
            count = 0
            for tool_name, tool in self._tools.items():
                if tool.domain == domain and tool_name in self._disabled_tools:
                    self._disabled_tools.remove(tool_name)
                    count += 1
            return count
        return 0

    def disable_domain(self, domain: str) -> int:
        """
        Disable all tools in a domain.

        Args:
            domain: Domain name to disable

        Returns:
            Number of tools disabled
        """
        count = 0
        if domain not in self._disabled_domains:
            self._disabled_domains.add(domain)
            # Disable all tools in this domain
            for tool_name, tool in self._tools.items():
                if tool.domain == domain and tool_name not in self._disabled_tools:
                    self._disabled_tools.add(tool_name)
                    count += 1
        return count

    def list_tool_domains(self) -> List[str]:
        """
        List all available tool domains.

        Returns:
            List of domain names
        """
        domains = set()
        for tool in self._tools.values():
            domains.add(tool.domain)
        return sorted(list(domains))

    def get_enabled_tools(self, domain: Optional[str] = None) -> List[ToolInfo]:
        """
        Get list of enabled tools.

        Args:
            domain: Optional filter by domain

        Returns:
            List of enabled ToolInfo objects
        """
        tools = []
        for tool in self._tools.values():
            # Check if tool is not disabled
            if (tool.name not in self._disabled_tools and
                (domain is None or tool.domain == domain)):
                tools.append(tool)
        return tools

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
            ValueError: If tool not found or disabled
        """
        # Check if tool is disabled
        if name in self._disabled_tools:
            raise ValueError(f"Tool is disabled: {name}")

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
