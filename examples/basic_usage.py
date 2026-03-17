#!/usr/bin/env python3
"""
Basic usage example for BioAgent.

This example demonstrates how to use BioAgent programmatically.
"""

import asyncio
from bioagent.agent import Agent
from bioagent.config import BioAgentConfig


async def main():
    """Run a basic BioAgent query."""
    # Load configuration from environment
    config = BioAgentConfig.from_env()
    config.validate()

    # Create agent
    agent = Agent(config=config)

    # Run queries
    queries = [
        "查询 TP53 基因的功能",
        "Search for insulin protein in UniProt",
        "Find recent papers about CRISPR"
    ]

    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        response = await agent.execute(query)
        print(f"\n{response}")

        # Print summary
        summary = agent.get_summary()
        print(f"\n{'-'*60}")
        print(f"Session Summary:")
        print(f"  Messages: {summary['state']['message_count']}")
        print(f"  Tool calls: {summary['state']['tool_calls']}")
        print(f"  LLM calls: {summary['state']['llm_calls']}")
        print(f"  Cost: ${summary['costs']['total_cost']:.4f}")
        print(f"  Tokens: {summary['costs']['total_tokens']}")
        print('-'*60)

        # Reset for next query
        agent.reset()


if __name__ == "__main__":
    asyncio.run(main())
