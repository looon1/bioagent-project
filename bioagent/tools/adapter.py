"""
Tool adapter for integrating external tool libraries.

Provides adapters for integrating tools from external libraries like Biomni
into the bioagent tool system.
"""

import ast
import importlib
import inspect
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from bioagent.tools.base import ToolInfo, tool
from bioagent.tools.registry import ToolRegistry


class ToolAdapter:
    """
    Adapter for integrating external tool libraries into bioagent.

    This class provides a wrapper pattern to integrate tools from external
    libraries (like Biomni) into the bioagent tool registry.
    """

    def __init__(self, registry: ToolRegistry, logger=None):
        """
        Initialize the tool adapter.

        Args:
            registry: The ToolRegistry to register tools to
            logger: Optional logger for logging adapter activities
        """
        self.registry = registry
        self.logger = logger
        self._external_tools: Dict[str, Dict[str, Any]] = {}
        self._disabled_domains: Set[str] = set()
        self._disabled_tools: Set[str] = set()

    def register_biomni_tools(
        self,
        biomni_path: Optional[str] = None,
        domains: Optional[List[str]] = None
    ) -> int:
        """
        Register Biomni tools to the tool registry.

        This method now directly reads and parses tool description files
        to avoid import dependency issues with biomni.utils.

        Args:
            biomni_path: Optional custom path to Biomni installation.
                        If None, uses system path.
            domains: Optional list of domains to load (e.g., ["genetics", "genomics"]).
                      If None, loads all available domains.

        Returns:
            Number of tools registered.
        """
        # Determine tool description directory
        if biomni_path:
            tool_desc_dir = Path(biomni_path) / "biomni" / "tool" / "tool_description"
        else:
            # Try to find biomni in system path
            import importlib.util
            spec = importlib.util.find_spec("biomni")
            if spec and spec.origin:
                biomni_path = Path(spec.origin).parent
                tool_desc_dir = biomni_path / "tool" / "tool_description"
            else:
                if self.logger:
                    self.logger.warning(
                        "Biomni not found in system path. Skipping Biomni tool integration."
                    )
                return 0

        # Available domains (matching biomni's structure)
        all_domains = [
            "biochemistry", "bioengineering", "bioimaging", "biophysics",
            "cancer_biology", "cell_biology", "database", "genetics",
            "genomics", "glycoengineering", "immunology", "lab_automation",
            "literature", "microbiology", "molecular_biology",
            "pathology", "pharmacology", "physiology", "protocols",
            "synthetic_biology", "systems_biology", "support_tools"
        ]

        # Filter domains if specified
        available_domains = [d for d in all_domains if (domains is None or d in domains)]

        # Register tools from each domain
        registered_count = 0
        for domain in available_domains:
            try:
                count = self._load_biomni_description_file(domain, tool_desc_dir)
                registered_count += count
            except Exception as e:
                if self.logger:
                    self.logger.warning(
                        f"Failed to load Biomni module {domain}: {e}"
                    )
                continue

        if self.logger:
            self.logger.info(
                f"Registered {registered_count} Biomni tools from {len(available_domains)} domains"
            )

        return registered_count

    def _load_biomni_description_file(
        self,
        domain: str,
        tool_desc_dir: Path
    ) -> int:
        """
        Load tool descriptions from a single domain file using AST parsing.

        Args:
            domain: Domain name (e.g., "genetics")
            tool_desc_dir: Path to tool_description directory

        Returns:
            Number of tools registered.
        """
        # Read and parse the description file directly
        desc_file = tool_desc_dir / f"{domain}.py"

        if not desc_file.exists():
            if self.logger:
                self.logger.debug(f"Description file not found: {desc_file}")
            return 0

        try:
            # Read the file content
            with open(desc_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse the description variable using AST
            tree = ast.parse(content)

            # Find the assignment to 'description'
            tool_descriptions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    # Check if this is an assignment to 'description'
                    if isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'description':
                        # The value should be a list
                        if isinstance(node.value, ast.List):
                            for element in node.value.elts:
                                if isinstance(element, ast.Dict):
                                    # Extract the dictionary as Python literal
                                    tool_dict = ast.literal_eval(ast.get_source_segment(element))
                                    if isinstance(tool_dict, dict) and 'name' in tool_dict:
                                        tool_descriptions.append(tool_dict)

            if self.logger:
                self.logger.debug(f"Parsed {len(tool_descriptions)} tool descriptions from {domain}")

        except Exception as e:
            if self.logger:
                self.logger.debug(f"Could not parse {desc_file}: {e}")
                import traceback
                traceback.print_exc()
            return 0

        registered_count = 0

        # Create bioagent tools for each description
        for tool_desc in tool_descriptions:
            tool_name = tool_desc.get("name")
            if not tool_name:
                continue

            # Wrap the tool (function may or may not exist)
            wrapped_tool = self._wrap_biomni_tool(
                tool_func=None,  # Function may not be available
                tool_desc=tool_desc,
                domain=domain,
                module_name=f"biomni.tool.{domain}"
            )

            # Register to registry
            if wrapped_tool:
                try:
                    self.registry.register(wrapped_tool)
                    registered_count += 1
                except ValueError:
                    # Tool already registered, skip
                    continue

        return registered_count

    def _wrap_biomni_tool(
        self,
        tool_func: Optional[Callable],
        tool_desc: Dict[str, Any],
        domain: str,
        module_name: str
    ) -> Optional[Callable]:
        """
        Wrap a Biomni tool as a bioagent tool.

        Args:
            tool_func: The actual Biomni function (may be None)
            tool_desc: Tool description dictionary
            domain: Domain category for tool
            module_name: Module name for reference

        Returns:
            Wrapped function or None if wrapping fails
        """
        tool_name = tool_desc.get("name", "")
        description = tool_desc.get("description", "")

        # Extract parameters from description
        required_params = tool_desc.get("required_parameters", [])
        optional_params = tool_desc.get("optional_parameters", [])

        # Build parameter documentation string
        param_doc = "\n".join([
            f"    {p['name']}: {p.get('description', '')}"
            for p in required_params + optional_params
        ])

        # Build docstring
        docstring = f"{description}\n\nArgs:\n{param_doc}\n\n"

        # Create wrapper function
        @tool(domain=domain)
        async def wrapped_tool(**kwargs) -> Any:
            # Check if tool function is available
            if tool_func is None:
                # Tool function not available, return informative message
                return f"Tool '{tool_name}' is registered but the underlying function is not available. This may require additional dependencies that are not installed."

            # Call the actual Biomni function
            try:
                if inspect.iscoroutinefunction(tool_func):
                    return await tool_func(**kwargs)
                else:
                    return tool_func(**kwargs)
            except Exception as e:
                return {"error": str(e)}

        # Set metadata
        wrapped_tool.__name__ = tool_name
        wrapped_tool.__doc__ = docstring
        wrapped_tool._biomni_module = module_name
        wrapped_tool._is_external = True

        return wrapped_tool

    def enable_domain(self, domain: str) -> int:
        """
        Enable all tools in a domain.

        Args:
            domain: Domain name to enable

        Returns:
            Number of tools enabled.
        """
        if domain in self._disabled_domains:
            self._disabled_domains.remove(domain)

        # Re-register tools from this domain
        count = 0
        for tool_info in self.registry.list_tools(domain=domain):
            if tool_info.name in self._disabled_tools:
                self._disabled_tools.remove(tool_info.name)
                count += 1

        return count

    def disable_domain(self, domain: str) -> int:
        """
        Disable all tools in a domain.

        Args:
            domain: Domain name to disable

        Returns:
            Number of tools disabled.
        """
        self._disabled_domains.add(domain)

        # Add all tools in this domain to disabled set
        count = 0
        for tool_info in self.registry.list_tools(domain=domain):
            self._disabled_tools.add(tool_info.name)
            count += 1

        return count

    def enable_tool(self, tool_name: str) -> bool:
        """
        Enable a specific tool.

        Args:
            tool_name: Name of the tool to enable

        Returns:
            True if tool was disabled and now enabled, False otherwise
        """
        if tool_name in self._disabled_tools:
            self._disabled_tools.remove(tool_name)
            return True
        return False

    def disable_tool(self, tool_name: str) -> bool:
        """
        Disable a specific tool.

        Args:
            tool_name: Name of the tool to disable

        Returns:
            True if tool was enabled and now disabled, False otherwise
        """
        if tool_name not in self._disabled_tools:
            self._disabled_tools.add(tool_name)
            return True
        return False

    def get_enabled_tools(self, domain: Optional[str] = None) -> List[ToolInfo]:
        """
        Get list of enabled tools.

        Args:
            domain: Optional filter by domain

        Returns:
            List of enabled ToolInfo objects
        """
        all_tools = self.registry.list_tools(domain=domain)
        return [
            t for t in all_tools
            if t.name not in self._disabled_tools
        ]

    def list_available_domains(self) -> List[str]:
        """
        List all available domains from registered tools.

        Returns:
            Sorted list of domain names
        """
        domains = set()
        for tool_info in self.registry.list_tools():
            domains.add(tool_info.domain)
        return sorted(list(domains))

    def list_external_tools(self) -> Dict[str, List[str]]:
        """
        List all external tools by domain.

        Returns:
            Dictionary mapping domain names to lists of tool names
        """
        result = {}
        for tool_info in self.registry.list_tools():
            if hasattr(tool_info, '_is_external') and tool_info._is_external:
                domain = tool_info.domain
                if domain not in result:
                    result[domain] = []
                result[domain].append(tool_info.name)
        return result


class BiomniToolAdapter(ToolAdapter):
    """
    Specialized adapter for Biomni tool integration.

    Provides Biomni-specific functionality for tool management.
    """

    def __init__(self, registry: ToolRegistry, logger=None, biomni_path: Optional[str] = None):
        """
        Initialize the Biomni tool adapter.

        Args:
            registry: The ToolRegistry to register tools to
            logger: Optional logger for logging adapter activities
            biomni_path: Optional custom path to Biomni installation
        """
        super().__init__(registry, logger)
        self.biomni_path = biomni_path

    def register_all(self, domains: Optional[List[str]] = None) -> int:
        """
        Register all Biomni tools.

        Args:
            domains: Optional list of domains to load

        Returns:
            Number of tools registered
        """
        return self.register_biomni_tools(
            biomni_path=self.biomni_path,
            domains=domains
        )

    def get_tool_by_function_name(self, function_name: str) -> Optional[Callable]:
        """
        Get a tool function by its original Biomni name.

        Args:
            function_name: The original function name in Biomni

        Returns:
            The tool function or None if not found
        """
        for domain, info in self._external_tools.items():
            module = info.get("module")
            if module and hasattr(module, function_name):
                return getattr(module, function_name)
        return None

    def get_tool_description(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the original tool description from Biomni.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool description dictionary or None if not found
        """
        for domain, info in self._external_tools.items():
            descriptions = info.get("descriptions", [])
            for desc in descriptions:
                if desc.get("name") == tool_name:
                    return desc
        return None
