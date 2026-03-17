"""
Test Agent with actual API key.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bioagent.config import BioAgentConfig
from bioagent.agent import Agent


async def main():
    print("=" * 60)
    print("Agent Integration Test with API Key")
    print("=" * 60)

    # Configure with user's API key
    config = BioAgentConfig()
    config.api_key = "a0412f4ae9de4b7b8cef2403f3f7f506.abcOoGU4eofGiaAk"
    config.base_url = "https://open.bigmodel.cn/api/coding/paas/v4"
    config.model = "glm-4-flash"  # Use a model compatible with the endpoint

    print(f"\nConfiguration:")
    print(f"  Base URL: {config.base_url}")
    print(f"  Model: {config.model}")
    print(f"  API Key: {config.api_key[:20]}...")

    try:
        # Create agent
        agent = Agent(config=config)

        print(f"\nAgent initialized:")
        print(f"  Session ID: {agent.session_id}")
        print(f"  Tools loaded: {len(agent.tool_registry)}")
        print(f"  Tool domains: {agent.list_tool_domains()}")

        # Test a simple query (uses core tools)
        print("\n" + "=" * 60)
        print("Test 1: Simple greeting query")
        print("=" * 60)
        result = await agent.execute("Hello, please introduce yourself.")
        print(f"\nResponse: {result}")

        # Test file operation
        print("\n" + "=" * 60)
        print("Test 2: File write and read")
        print("=" * 60)
        result = await agent.execute(
            "Create a file named 'test.txt' with content 'Hello BioAgent Phase 2!'"
        )
        print(f"\nResponse: {result}")

        # Test code execution
        print("\n" + "=" * 60)
        print("Test 3: Python code execution")
        print("=" * 60)
        result = await agent.execute(
            "Write a Python function to calculate the sum of first 10 numbers and call it."
        )
        print(f"\nResponse: {result}")

        # Get summary
        print("\n" + "=" * 60)
        print("Session Summary")
        print("=" * 60)
        summary = agent.get_summary()
        print(f"  Session ID: {summary['session_id']}")
        print(f"  State: {summary['state']}")
        print(f"  Total tool calls: {summary['state']['tool_calls']}")
        print(f"  Total LLM calls: {summary['state']['llm_calls']}")
        print(f"  Metrics: {summary.get('metrics', {})}")

        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
