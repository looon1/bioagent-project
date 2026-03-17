"""
Phase 2 Demo: External Tool Integration and Multi-Agent Teams.

This script demonstrates the new Phase 2 features:
1. Tool adapter integration with Biomni
2. Domain-based tool management
3. Sequential team execution
4. Hierarchical team execution
"""

import asyncio
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from bioagent.config import BioAgentConfig
from bioagent.agent import Agent
from bioagent.agents import SequentialTeam, HierarchicalTeam


async def demo_biomni_integration():
    """Demonstrate Biomni tool integration."""
    print("\n" + "=" * 60)
    print("Demo 1: Biomni Tool Integration")
    print("=" * 60)

    # Configure with Biomni enabled
    config = BioAgentConfig()
    config.enable_biomni_tools = True
    config.biomni_path = "/mnt/public/rstudio-home/fzh_hblab/Biomni-Web-main"
    config.biomni_domains = ["genetics", "genomics"]  # Load specific domains
    # Note: API key is required for actual execution
    # config.api_key = "your_api_key_here"

    try:
        agent = Agent(config=config)

        # List available domains
        domains = agent.list_tool_domains()
        print(f"Available domains: {domains[:5]}... (and more)")

        # Domain management
        print(f"Disabling 'genetics' domain...")
        agent.disable_tool_domain("genetics")

        print(f"Enabling 'genomics' domain...")
        agent.enable_tool_domain("genomics")

        print("\nNote: Uncomment the API key and execute line to test with actual queries:")
        # result = await agent.execute("Perform a simple genetic analysis")
        # print(f"Result: {result}")

    except Exception as e:
        print(f"Note: Agent initialization requires API key. Error: {e}")


async def demo_sequential_team():
    """Demonstrate sequential team execution."""
    print("\n" + "=" * 60)
    print("Demo 2: Sequential Team Execution")
    print("=" * 60)

    # Create two agents with different system prompts
    config = BioAgentConfig()
    # Note: API key required
    # config.api_key = "your_api_key_here"

    try:
        # Create agents with specialized roles
        agent1 = Agent(
            config=config,
            system_prompt="You are a research analyst. Extract key facts."
        )

        agent2 = Agent(
            config=config,
            system_prompt="You are a summary writer. Create concise summaries."
        )

        # Create sequential team
        team = SequentialTeam([agent1, agent2], connect_prompt="Summarize:")

        print("Created sequential team with 2 agents")
        print("Note: Uncomment API key and execute to test:")
        # result = await team.execute("Analyze TP53 gene function")
        # print(f"Final result: {result}")

    except Exception as e:
        print(f"Note: Team execution requires API key. Error: {e}")


async def demo_hierarchical_team():
    """Demonstrate hierarchical team execution."""
    print("\n" + "=" * 60)
    print("Demo 3: Hierarchical Team Execution")
    print("=" * 60)

    config = BioAgentConfig()
    # Note: API key required
    # config.api_key = "your_api_key_here"

    try:
        # Create supervisor
        supervisor = Agent(
            config=config,
            system_prompt="You are a task coordinator. Analyze requests and delegate appropriately."
        )

        # Create specialized sub-agents
        genetics_agent = Agent(
            config=config,
            system_prompt="You are a genetics specialist. Answer genetics questions."
        )

        genomics_agent = Agent(
            config=config,
            system_prompt="You are a genomics specialist. Answer genomics questions."
        )

        # Create hierarchical team
        team = HierarchicalTeam(supervisor, [genetics_agent, genomics_agent])

        print("Created hierarchical team:")
        print(f"  - Supervisor: {supervisor.session_id}")
        print(f"  - Sub-agents: {[a.session_id for a in [genetics_agent, genomics_agent]]}")
        print("Note: Uncomment API key and execute to test:")
        # result = await team.execute("What is the relationship between gene and genome?")
        # print(f"Result: {result}")

    except Exception as e:
        print(f"Note: Team execution requires API key. Error: {e}")


async def demo_tool_management():
    """Demonstrate domain-based tool management."""
    print("\n" + "=" * 60)
    print("Demo 4: Tool Domain Management")
    print("=" * 60)

    config = BioAgentConfig()
    # config.api_key = "your_api_key_here"

    try:
        agent = Agent(config=config)

        print("\nAvailable tool domains:")
        domains = agent.list_tool_domains()
        for domain in domains:
            print(f"  - {domain}")

        print("\nDomain management methods:")
        print("  - enable_tool_domain(domain)")
        print("  - disable_tool_domain(domain)")
        print("  - list_tool_domains()")

    except Exception as e:
        print(f"Note: Agent initialization requires API key. Error: {e}")


async def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("Phase 2 Feature Demos")
    print("=" * 60)

    # Run demos
    await demo_biomni_integration()
    await demo_sequential_team()
    await demo_hierarchical_team()
    await demo_tool_management()

    print("\n" + "=" * 60)
    print("Demos complete!")
    print("=" * 60)
    print("\nNote: To test actual functionality:")
    print("1. Set your API key as ANTHROPIC_API_KEY environment variable")
    print("2. Uncomment the execute() calls in each demo")
    print("3. Run: python examples/phase2_demo.py")


if __name__ == "__main__":
    asyncio.run(main())
