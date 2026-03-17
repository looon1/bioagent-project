"""
Tool loader for BioAgent.

Dynamically loads tools from directories and modules.
"""

import importlib
import importlib.util
import inspect
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from bioagent.tools.base import ToolInfo, is_tool, get_tool_info
from bioagent.tools.registry import ToolRegistry


class ToolLoader:
    """Load tools from various sources."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def load_from_directory(self, directory: str) -> None:
        """
        Load all tools from a Python directory.

        Args:
            directory: Path to the directory containing tool modules
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            print(f"Tool directory does not exist: {directory}")
            return

        # Find all Python files
        for py_file in dir_path.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            module_name = f"{dir_path.name}.{py_file.stem}"

            try:
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    # Register tools from the module
                    for name, obj in inspect.getmembers(module):
                        if is_tool(obj):
                            self.registry.register(obj)

            except Exception as e:
                print(f"Failed to load tools from {py_file}: {e}")

    def load_from_json(self, json_file: str) -> None:
        """
        Load tool descriptions from a JSON file.

        This is for Phase 2 - declarative tool definitions.

        Args:
            json_file: Path to the JSON file containing tool descriptions
        """
        json_path = Path(json_file)

        if not json_path.exists():
            print(f"Tool description file does not exist: {json_file}")
            return

        try:
            with open(json_path, 'r') as f:
                data = json.load(f)

            if "tools" not in data:
                print(f"Invalid tool description file: {json_file}")
                return

            for tool_desc in data["tools"]:
                # Create a stub function for the tool
                def _stub(**kwargs):
                    raise NotImplementedError(
                        f"Tool {tool_desc['name']} is not implemented yet"
                    )

                # Create ToolInfo from JSON
                tool_info = ToolInfo(
                    name=tool_desc["name"],
                    description=tool_desc.get("description", ""),
                    parameters=tool_desc.get("parameters", {}),
                    func=_stub,
                    domain=tool_desc.get("domain", "general")
                )

                # Register (stub for now)
                self.registry._tools[tool_info["name"]] = tool_info

        except Exception as e:
            print(f"Failed to load tool descriptions from {json_file}: {e}")

    def load_descriptions_from_directory(self, directory: str) -> None:
        """
        Load all JSON tool descriptions from a directory.

        Args:
            directory: Path to the directory containing JSON description files
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            print(f"Tool descriptions directory does not exist: {directory}")
            return

        for json_file in dir_path.glob("*.json"):
            self.load_from_json(json_file)
