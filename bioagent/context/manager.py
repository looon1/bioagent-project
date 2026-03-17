"""
Context Manager for BioAgent.

Manages context compression across three layers:
- micro_compact: Silent, every turn
- auto_compact: When token threshold is exceeded
- manual compact: Tool-triggered
"""

import asyncio
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

from bioagent.config import BioAgentConfig
from bioagent.llm import Message as LLMMessage
from bioagent.context.compressors import (
    MicroCompressor,
    AutoCompressor,
    estimate_tokens
)

if TYPE_CHECKING:
    from bioagent.llm import LLMProvider


class ContextManager:
    """
    Manages context compression for BioAgent.

    Coordinates between compression strategies and provides
    unified interface for the agent.
    """

    def __init__(self, config: BioAgentConfig, logger=None):
        """
        Initialize context manager.

        Args:
            config: BioAgent configuration
            logger: Logger instance
        """
        self.config = config
        self.logger = logger

        # Compression settings
        self.max_tokens = config.context_max_tokens
        self.keep_recent = config.context_keep_recent

        # Compressors
        self.micro_compressor = MicroCompressor(keep_recent=self.keep_recent)
        self.auto_compressor: Optional[AutoCompressor] = None

        # Statistics
        self.micro_compact_count = 0
        self.auto_compact_count = 0
        self.manual_compact_count = 0

    def set_llm_provider(self, llm_provider: "LLMProvider") -> None:
        """
        Set LLM provider for auto compressor (requires async summarization).

        Args:
            llm_provider: LLM provider instance
        """
        self.auto_compressor = AutoCompressor(
            llm_provider=llm_provider,
            transcripts_dir=self.config.transcripts_dir,
            logger=self.logger
        )

    def estimate_tokens(self, messages: List[LLMMessage]) -> int:
        """
        Estimate token count for message list.

        Args:
            messages: List of LLM messages

        Returns:
            Estimated token count
        """
        return estimate_tokens(messages)

    def should_compress(self, messages: List[LLMMessage]) -> bool:
        """
        Check if compression is needed based on token count.

        Args:
            messages: List of LLM messages

        Returns:
            True if compression should be triggered
        """
        estimated = self.estimate_tokens(messages)
        should = estimated >= self.max_tokens

        if should and self.logger:
            self.logger.info(
                "Compression threshold reached",
                estimated_tokens=estimated,
                threshold=self.max_tokens
            )

        return should

    def micro_compact(self, messages: List[LLMMessage]) -> List[LLMMessage]:
        """
        Apply micro compression (silent layer).

        Replaces old tool results with placeholders.

        Args:
            messages: List of LLM messages

        Returns:
            Compressed message list
        """
        compressed = self.micro_compressor.compress(messages)
        self.micro_compact_count += 1

        if self.logger:
            self.logger.debug(
                "Micro compression applied",
                original_count=len(messages),
                compressed_count=len(compressed)
            )

        return compressed

    async def auto_compress(
        self,
        messages: List[LLMMessage],
        focus: str = ""
    ) -> List[LLMMessage]:
        """
        Apply auto compression (threshold layer).

        Saves transcript, summarizes, and replaces messages.

        Args:
            messages: List of LLM messages
            focus: Optional focus area to preserve

        Returns:
            Compressed message list
        """
        if self.auto_compressor is None:
            if self.logger:
                self.logger.warning("Auto compressor not initialized (no LLM provider)")
            return messages

        compressed = await self.auto_compressor.compress(messages, focus)
        self.auto_compact_count += 1

        return compressed

    async def manual_compress(
        self,
        messages: List[LLMMessage],
        focus: str = ""
    ) -> List[LLMMessage]:
        """
        Apply manual compression (tool-triggered layer).

        Same as auto_compress but tracks separately.

        Args:
            messages: List of LLM messages
            focus: Optional focus area to preserve

        Returns:
            Compressed message list
        """
        if self.auto_compressor is None:
            if self.logger:
                self.logger.warning("Manual compressor not initialized (no LLM provider)")
            return messages

        compressed = await self.auto_compressor.compress(messages, focus)
        self.manual_compact_count += 1

        if self.logger:
            self.logger.info("Manual compression triggered")

        return compressed

    def get_stats(self) -> dict:
        """
        Get compression statistics.

        Returns:
            Dictionary with compression stats
        """
        return {
            "micro_compacts": self.micro_compact_count,
            "auto_compacts": self.auto_compact_count,
            "manual_compacts": self.manual_compact_count,
            "total_compacts": (
                self.micro_compact_count +
                self.auto_compact_count +
                self.manual_compact_count
            )
        }

    def reset_stats(self) -> None:
        """Reset compression statistics."""
        self.micro_compact_count = 0
        self.auto_compact_count = 0
        self.manual_compact_count = 0
