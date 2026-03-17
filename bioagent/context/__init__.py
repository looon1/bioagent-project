"""
Context management system for BioAgent.

Provides three-layer compression pipeline:
1. micro_compact - Silent, every turn - replace old tool results with placeholders
2. auto_compact - Triggered when tokens exceed threshold - save, summarize, replace
3. manual compact - Tool-triggered immediate summarization
"""
from .manager import ContextManager
from .compressors import MicroCompressor, AutoCompressor

__all__ = ["ContextManager", "MicroCompressor", "AutoCompressor"]
