"""CLI entry point for launching the BioAgent Web UI.

Usage:
    bioagent-web                        # default port 7860
    bioagent-web --port 8080            # custom port
    bioagent-web --host 127.0.0.1       # localhost only
    bioagent-web --model claude-sonnet-4  # specify model
"""

import argparse
import sys


def main():
    """Main entry point for bioagent-web CLI."""
    parser = argparse.ArgumentParser(
        prog="bioagent-web",
        description="Launch the BioAgent Web UI (FastAPI + SSE streaming)",
    )
    parser.add_argument("--port", type=int, default=7860,
                    help="Port to bind to (default: 7860)")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                    help="Host/IP to bind to (default: 0.0.0.0)")
    parser.add_argument("--model", type=str, default=None,
                    help="LLM model to use")
    parser.add_argument("--base-url", type=str, default=None,
                    help="Custom API base URL")
    parser.add_argument("--reload", action="store_true",
                    help="Enable auto-reload for development")

    args = parser.parse_args()

    # Lazy import so --help is fast
    from bioagent.agent import Agent
    from bioagent.config import BioAgentConfig

    # Build config
    config = BioAgentConfig.from_env()
    config.web_host = args.host
    config.web_port = args.port

    if args.model:
        config.model = args.model
    if args.base_url:
        config.base_url = args.base_url

    # Validate config
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Initialize agent
    print("Initializing BioAgent...")
    agent = Agent(config=config)

    # Create and serve app
    from bioagent.web.server import create_app
    import uvicorn

    app = create_app(agent, config)

    print(f"Starting BioAgent Web UI on http://{args.host}:{args.port}")
    print(f"Model: {config.model}")
    print(f"Press Ctrl+C to stop")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
