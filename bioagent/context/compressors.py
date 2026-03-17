"""
Compression strategies for BioAgent context management.

Two compression layers:
- MicroCompressor: Silent, every turn - replace old tool results with placeholders
- AutoCompressor: Triggered when tokens exceed threshold - save, summarize, replace
"""

import json
import re
import time
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

from bioagent.llm import Message as LLMMessage

if TYPE_CHECKING:
    from bioagent.llm import LLMProvider


class MicroCompressor:
    """
    Replace old tool results with placeholders.

    Keeps the last N tool results and replaces older results with placeholders.
    This runs silently every turn to gradually reduce context size.
    """

    def __init__(self, keep_recent: int = 3):
        """
        Initialize micro compressor.

        Args:
            keep_recent: Number of most recent tool results to keep
        """
        self.keep_recent = keep_recent

    def compress(self, messages: List[LLMMessage]) -> List[LLMMessage]:
        """
        Apply micro compression to messages.

        Finds tool role messages, keeps the last N, and replaces others
        with placeholders.

        Args:
            messages: List of LLM messages

        Returns:
            Compressed message list
        """
        if self.keep_recent < 0:
            return messages

        # Find tool messages and their positions
        tool_messages = [(i, msg) for i, msg in enumerate(messages)
                         if msg.role == "tool"]

        if len(tool_messages) <= self.keep_recent:
            return messages  # No compression needed

        # Keep only the last N tool messages
        keep_tool_indices = {idx for idx, _ in tool_messages[-self.keep_recent:]}
        tool_names = {}

        # Build tool name lookup from assistant messages
        for i, msg in enumerate(messages):
            if msg.role == "assistant" and hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_names[tc.id] = tc.name

        compressed = []
        for i, msg in enumerate(messages):
            if msg.role == "tool" and i not in keep_tool_indices:
                # Replace with placeholder
                tool_call_id = msg.tool_call_id if hasattr(msg, "tool_call_id") else ""
                tool_name = tool_names.get(tool_call_id, "unknown")
                placeholder = LLMMessage(
                    role="tool",
                    content=f"[Previous: used {tool_name}]",
                    tool_call_id=tool_call_id
                )
                compressed.append(placeholder)
            else:
                compressed.append(msg)

        return compressed


class AutoCompressor:
    """
    Save transcript, summarize, and replace all messages.

    This runs when token count exceeds threshold. It:
    1. Saves full transcript to disk
    2. Asks LLM to summarize conversation
    3. Replaces all messages with compressed summary
    """

    def __init__(
        self,
        llm_provider: "LLMProvider",
        transcripts_dir: Path,
        logger=None
    ):
        """
        Initialize auto compressor.

        Args:
            llm_provider: LLM provider for summarization
            transcripts_dir: Directory for saving transcripts
            logger: Logger instance
        """
        self.llm_provider = llm_provider
        self.transcripts_dir = transcripts_dir
        self.logger = logger

    def compress(
        self,
        messages: List[LLMMessage],
        focus: str = ""
    ) -> List[LLMMessage]:
        """
        Apply auto compression to messages.

        Args:
            messages: List of LLM messages
            focus: Optional focus area to preserve in summary

        Returns:
            Compressed message list with summary
        """
        if self.logger:
            self.logger.info("Auto compression started")

        # Save full transcript
        transcript_path = self._save_transcript(messages)
        if self.logger:
            self.logger.info(f"Transcript saved to {transcript_path}")

        # Generate summary
        summary = self._summarize(messages, focus)

        # Replace messages with compressed version
        compressed = self._create_compressed_messages(summary)

        if self.logger:
            self.logger.info(f"Compression complete: {len(messages)} -> {len(compressed)} messages")

        return compressed

    def _save_transcript(self, messages: List[LLMMessage]) -> Path:
        """
        Save full transcript to disk.

        Args:
            messages: List of LLM messages

        Returns:
            Path to saved transcript file
        """
        timestamp = int(time.time())
        filename = f"transcript_{timestamp}.jsonl"
        path = self.transcripts_dir / filename

        # Convert messages to serializable format
        serializable = []
        for msg in messages:
            msg_dict = {
                "role": msg.role,
                "content": msg.content
            }
            if hasattr(msg, "tool_call_id") and msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            if hasattr(msg, "tool_name") and msg.tool_name:
                msg_dict["tool_name"] = msg.tool_name
            if hasattr(msg, "tool_args") and msg.tool_args:
                msg_dict["tool_args"] = msg.tool_args
            serializable.append(msg_dict)

        # Save as JSONL (one JSON object per line)
        with open(path, "w", encoding="utf-8") as f:
            for item in serializable:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        return path

    async def _summarize(self, messages: List[LLMMessage], focus: str = "") -> str:
        """
        Ask LLM to summarize the conversation.

        Args:
            messages: List of LLM messages to summarize
            focus: Optional focus area

        Returns:
            Summary text
        """
        # Build conversation text for summarization
        conversation_text = "\n\n".join(
            f"{msg.role}: {msg.content}" for msg in messages
        )

        focus_prompt = f"\nFocus area: {focus}" if focus else ""

        summary_prompt = f"""Please summarize the following conversation in a concise way.

Include:
1. What has been accomplished so far
2. Current state of the conversation
3. Any key decisions or findings
{focus_prompt}

Conversation:
{conversation_text}

Provide a summary that preserves all critical information."""

        try:
            response = await self.llm_provider.call(
                messages=[LLMMessage(role="user", content=summary_prompt)],
                tools=None
            )
            return response.content or "Summary generation failed"
        except Exception as e:
            if self.logger:
                self.logger.error(f"Summary generation failed: {e}")
            return "Summary generation failed. See transcript file for full history."

    def _create_compressed_messages(self, summary: str) -> List[LLMMessage]:
        """
        Create compressed message list from summary.

        Args:
            summary: Summary text

        Returns:
            List with system and summary messages
        """
        return [
            LLMMessage(role="user", content=summary)
        ]


def estimate_tokens(messages: List[LLMMessage]) -> int:
    """
    Rough token estimation for message list.

    Uses simple heuristic: 4 characters per token on average.

    Args:
        messages: List of LLM messages

    Returns:
        Estimated token count
    """
    text = str(messages)
    return len(text) // 4
