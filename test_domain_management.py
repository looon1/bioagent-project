"""
Test domain management functionality without API key.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bioagent.config import BioAgentConfig
from bioagent.agent import Agent
from bioagent.tools.base import tool

# Create test tools in different domains
@tool(domain="genetics")
async def genetics_tool(gene: str) -> str:
    """Analyze genetics information.

    Args:
        gene: Gene name

    Returns:
        Analysis result
    """
    return f"Genetics analysis for {gene}"

@tool(domain="genomics")
async def genomics_tool(data: str) -> str:
    """Analyze genomics data.

    Args:
        data: Data to analyze

    Returns:
        Analysis result
    """
    return f"Genomics analysis for {data}"

@tool(domain="pharmacology")
async def pharmacology_tool(drug: str) -> str:
    """Analyze pharmacology information.

    Args:
        drug: Drug name

    Returns:
        Analysis result
    """
    return f"Pharmacology analysis for {drug}"


def main():
    print("=" * 60)
    print("Domain Management Test")
    print("=" * 60)

    # Use the actual tool adapter system
    from bioagent.tools.registry import ToolRegistry
    from bioagent.tools.adapter import ToolAdapter

    # Create registry and adapter
    registry = ToolRegistry()
    registry.register(genetics_tool)
    registry.register(genomics_tool)
    registry.register(pharmacology_tool)

    # Use single adapter instance to maintain state
    adapter = ToolAdapter(registry)

    # List all domains
    print("\nAvailable domains:")
    domains = adapter.list_available_domains()
    for domain in domains:
        print(f"  - {domain}")

    # Disable genetics domain
    print("\nDisabling 'genetics' domain...")
    count = adapter.disable_domain("genetics")
    print(f"  Disabled {count} tools")

    # Check enabled tools
    print("\nEnabled tools after disabling 'genetics':")
    enabled = adapter.get_enabled_tools()
    for tool in enabled:
        print(f"  - {tool.name} (domain: {tool.domain})")

    # Re-enable genetics domain
    print("\nRe-enabling 'genetics' domain...")
    count = adapter.enable_domain("genetics")
    print(f"  Enabled {count} tools")

    # Check enabled tools again
    print("\nEnabled tools after re-enabling 'genetics':")
    enabled = adapter.get_enabled_tools()
    for tool in enabled:
        print(f"  - {tool.name} (domain: {tool.domain})")

    # Test individual tool enable/disable
    print("\nTesting individual tool disable/enable...")
    adapter.disable_tool("genomics_tool")
    enabled = adapter.get_enabled_tools()
    enabled_names = [t.name for t in enabled]
    print(f"  After disabling 'genomics_tool': {enabled_names}")

    adapter.enable_tool("genomics_tool")
    enabled = adapter.get_enabled_tools()
    enabled_names = [t.name for t in enabled]
    print(f"  After re-enabling 'genomics_tool': {enabled_names}")

    print("\n" + "=" * 60)
    print("Domain management test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
