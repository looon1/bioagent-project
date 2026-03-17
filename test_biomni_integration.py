"""
Test Biomni tool integration.

This script tests the Biomni tool adapter functionality.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bioagent.config import BioAgentConfig
from bioagent.agent import Agent


async def test_biomni_integration():
    """Test Biomni tool integration."""
    print("=" * 60)
    print("Biomni Integration Test")
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
        # Create agent
        agent = Agent(config=config)

        print(f"\nAgent initialized:")
        print(f"  Session ID: {agent.session_id}")
        print(f"  Total tools: {len(agent.tool_registry)}")

        # List available domains
        domains = agent.list_tool_domains()
        print(f"\nAvailable tool domains ({len(domains)}):")
        for domain in sorted(domains):
            # Count tools in this domain
            tools_in_domain = agent.tool_registry.list_tools(domain=domain)
            print(f"  - {domain}: {len(tools_in_domain)} tools")

        # Try to use Biomni tools
        print("\n" + "=" * 60)
        print("Test 1: Query genetics information")
        print("=" * 60)
        result = await agent.execute(
            "Can you help me understand what gene enrichment analysis is? "
            "Please use any available tools to search for information."
        )
        print(f"\nResponse: {result[:500]}...")
        print("..." if len(result) > 500 else "")

        # Test domain management
        print("\n" + "=" * 60)
        print("Test 2: Domain management")
        print("=" * 60)

        # List genetics tools
        genetics_tools = agent.tool_registry.list_tools(domain="genetics")
        print(f"\nGenetics tools available: {len(genetics_tools)}")
        for tool in genetics_tools[:5]:  # Show first 5
            print(f"  - {tool.name}: {tool.description[:60]}...")

        # Disable genetics domain
        print("\nDisabling 'genetics' domain...")
        count = agent.disable_tool_domain("genetics")
        print(f"  Disabled {count} tools")

        # Verify disabled
        enabled = agent.tool_registry.list_tools()
        genetics_enabled = [t for t in enabled if t.domain == "genetics"]
        print(f"  Genetics tools enabled after disable: {len(genetics_enabled)}")

        # Re-enable genetics domain
        print("\nRe-enabling 'genetics' domain...")
        count = agent.enable_tool_domain("genetics")
        print(f"  Enabled {count} tools")

        # Verify re-enabled
        enabled = agent.tool_registry.list_tools()
        genetics_enabled = [t for t in enabled if t.domain == "genetics"]
        print(f"  Genetics tools enabled after re-enable: {len(genetics_enabled)}")

        # Get summary
        print("\n" + "=" * 60)
        print("Session Summary")
        print("=" * 60)
        summary = agent.get_summary()
        print(f"  Session ID: {summary['session_id']}")
        print(f"  Total tools loaded: {summary['state']['tool_calls']}")
        print(f"  LLM calls made: {summary['state']['llm_calls']}")

        print("\n" + "=" * 60)
        print("Biomni integration test completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_biomni_integration())
