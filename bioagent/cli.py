"""
Command-line interface for BioAgent.

Provides an interactive CLI for interacting with the agent.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from bioagent.agent import Agent
from bioagent.config import BioAgentConfig


async def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="BioAgent - Biomedical AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "query",
        nargs="*",
        help="Query to execute (if not provided, enters interactive mode)"
    )

    parser.add_argument(
        "--model", "-m",
        help="LLM model to use (default: from config)",
        default=None
    )

    parser.add_argument(
        "--api-key",
        help="API key for the LLM provider",
        default=None
    )

    parser.add_argument(
        "--interactive", "-i",
        help="Run in interactive mode",
        action="store_true"
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        help="Maximum tool iterations",
        default=None
    )

    parser.add_argument(
        "--verbose", "-v",
        help="Enable verbose output",
        action="store_true"
    )

    args = parser.parse_args()

    # Build configuration
    config = BioAgentConfig.from_env()

    if args.model:
        config.model = args.model
    if args.api_key:
        config.api_key = args.api_key
    if args.max_iterations:
        config.max_tool_iterations = args.max_iterations
    if args.verbose:
        config.log_level = "DEBUG"

    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    # Initialize agent
    print(f"Initializing BioAgent with model: {config.model}")
    agent = Agent(config=config)

    # Process query or run interactive
    if args.query:
        query = " ".join(args.query)
        print(f"\nQuery: {query}\n")
        response = await agent.execute(query)
        print(f"\n{response}")
        print_summary(agent)
    else:
        # Interactive mode (default or explicit)
        await interactive_mode(agent)

    return 0


async def interactive_mode(agent: Agent) -> None:
    """Run agent in interactive mode."""
    print("\n" + "="*60)
    print("BioAgent Interactive Mode")
    print("Type 'quit' or 'exit' to stop, 'summary' for session info")
    print("="*60 + "\n")

    while True:
        try:
            # Get user input
            query = input("You: ").strip()

            if not query:
                continue

            # Handle special commands
            if query.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break
            elif query.lower() == "summary":
                print_summary(agent)
                continue
            elif query.lower() == "reset":
                agent.reset()
                print("Session reset.")
                continue
            elif query.lower() == "help":
                print("""
Special commands:
  quit, exit, q  - Exit the agent
  summary         - Show session summary
  reset           - Reset the agent state
  help            - Show this help message
""")
                continue

            # Execute query
            print("Agent: ", end="", flush=True)
            response = await agent.execute(query)
            print(response)
            print()

        except KeyboardInterrupt:
            print("\nInterrupted. Type 'quit' to exit.")
        except EOFError:
            print("\nGoodbye!")
            break


def print_summary(agent: Agent) -> None:
    """Print session summary."""
    summary = agent.get_summary()

    print("\n" + "-"*60)
    print("Session Summary")
    print("-"*60)
    print(f"Session ID: {summary['session_id']}")
    print(f"Status: {summary['state']['status']}")
    print(f"Messages: {summary['state']['message_count']}")
    print(f"Tool calls: {summary['state']['tool_calls']}")
    print(f"LLM calls: {summary['state']['llm_calls']}")
    print("\nCosts:")
    costs = summary['costs']
    print(f"  Total cost: ${costs['total_cost']:.4f}")
    print(f"  Total tokens: {costs['total_tokens']}")
    print(f"  Input tokens: {costs['input_tokens']}")
    print(f"  Output tokens: {costs['output_tokens']}")
    print("-"*60 + "\n")


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
