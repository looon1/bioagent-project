"""
Test Agent tool management functionality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bioagent.config import BioAgentConfig
from bioagent.agent import Agent
from bioagent.tools.base import tool


@tool(domain="test")
async def test_tool(message: str) -> str:
    """A simple test tool.

    Args:
        message: Input message

    Returns:
        Processed message
    """
    return f"Tool processed: {message}"


def main():
    print("=" * 60)
    print("Agent Tool Management Test")
    print("=" * 60)

    # Create a mock configuration with a fake API key
    config = BioAgentConfig()
    config.api_key = "test_key_123"  # Mock API key for validation
    config.model = "claude-sonnet-4-20250514"

    # Create agent
    try:
        agent = Agent(config=config)

        print(f"\nAgent initialized with session ID: {agent.session_id}")
        print(f"Number of loaded tools: {len(agent.tool_registry)}")

        # List core tools
        core_tools = agent.tool_registry.list_tool_names(domain=None)
        print(f"\nCore tools loaded: {core_tools}")

        # Register custom tool
        agent.register_tool(test_tool)
        print(f"\nRegistered custom tool 'test_tool'")
        print(f"Total tools after registration: {len(agent.tool_registry)}")

        # List domains
        domains = agent.list_tool_domains()
        print(f"\nAvailable domains: {domains}")

        # Get tool info
        tool_info = agent.tool_registry.get_tool("test_tool")
        if tool_info:
            print(f"\nCustom tool info:")
            print(f"  Name: {tool_info.name}")
            print(f"  Domain: {tool_info.domain}")
            print(f"  Description: {tool_info.description[:50]}...")

        print("\n" + "=" * 60)
        print("Agent tool management test complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError during agent initialization: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
