"""
Test direct Biomni tool loading bypassing biomni package imports.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bioagent.config import BioAgentConfig
from bioagent.agent import Agent


async def test_biomni_direct():
    """Test direct Biomni tool loading."""
    print("=" * 60)
    print("Direct Biomni Tool Loading Test")
    print("=" * 60)

    # Configure with Biomni enabled
    config = BioAgentConfig()
    config.api_key = "a0412f4ae9de4b7b8cef2403f3f7f506.abcOoGU4eofGiaAk"
    config.base_url = "https://open.bigmodel.cn/api/coding/paas/v4"
    config.model = "glm-4-flash"
    config.enable_biomni_tools = True
    config.biomni_path = "/mnt/public/rstudio-home/fzh_hblab/Biomni-Web-main"

    print(f"\nConfiguration:")
    print(f"  Biomni enabled: {config.enable_biomni_tools}")
    print(f"  Biomni path: {config.biomni_path}")
    print(f"  API Key: {config.api_key[:20]}...")

    try:
        # Directly load Biomni tools from description files
        from bioagent.tools.adapter import BiomniToolAdapter
        from bioagent.tools.registry import ToolRegistry

        registry = ToolRegistry()
        adapter = BiomniToolAdapter(
            registry=registry,
            biomni_path=config.biomni_path
        )

        print("\nAttempting to load Biomni tools directly...")
        count = adapter.register_biomni_tools_direct()

        print(f"Successfully loaded {count} Biomni tools")

        # Create agent with pre-loaded tools
        agent = Agent(config=config)

        # Replace agent's registry with our pre-loaded one
        agent.tool_registry = registry
        agent.tool_adapter = adapter

        print(f"\nAgent initialized:")
        print(f"  Session ID: {agent.session_id}")
        print(f"  Total tools: {len(agent.tool_registry)}")

        # List available domains
        domains = agent.list_tool_domains()
        print(f"\nAvailable tool domains ({len(domains)}):")
        for domain in sorted(domains):
            tools_in_domain = agent.tool_registry.list_tools(domain=domain)
            print(f"  - {domain}: {len(tools_in_domain)} tools")

        # Test a simple query
        if count > 0:
            print("\n" + "=" * 60)
            print("Test: Query genetics information")
            print("=" * 60)
            result = await agent.execute(
                "What does gene enrichment analysis do? "
                "Please use any available tools."
            )
            print(f"\nResponse: {result[:500]}...")

        # Get summary
        print("\n" + "=" * 60)
        print("Session Summary")
        print("=" * 60)
        summary = agent.get_summary()
        print(f"  Session ID: {summary['session_id']}")
        print(f"  Total tools: {summary['state']['tool_calls']}")
        print(f"  LLM calls: {summary['state']['llm_calls']}")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_biomni_direct())
