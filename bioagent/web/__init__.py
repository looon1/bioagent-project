"""
BioAgent Web UI Module

Provides FastAPI backend with SSE streaming for real-time agent interaction.
"""

from bioagent.web.server import create_app

__all__ = ["create_app"]
