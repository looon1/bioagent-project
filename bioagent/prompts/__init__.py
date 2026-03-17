"""Prompt templates for BioAgent."""

from pathlib import Path

# Load system prompt from markdown file
_system_prompt_path = Path(__file__).parent / "system_prompt.md"
SYSTEM_PROMPT = _system_prompt_path.read_text(encoding="utf-8")

__all__ = ["SYSTEM_PROMPT"]
