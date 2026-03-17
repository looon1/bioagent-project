"""
LLM provider abstraction for BioAgent.

Supports multiple LLM providers with a unified interface.
"""

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from bioagent.config import BioAgentConfig


@dataclass
class Message:
    """A message in the conversation."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None


@dataclass
class ToolCall:
    """A tool call requested by the LLM."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    model: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    duration_ms: float = 0.0
    stop_reason: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: BioAgentConfig):
        self.config = config

    @abstractmethod
    async def call(
        self,
        messages: List[Message],
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Call the LLM with the given messages and optional tools.

        Args:
            messages: List of conversation messages
            tools: List of tool descriptions
            **kwargs: Additional parameters for the specific provider

        Returns:
            LLMResponse with the model's response
        """
        pass

    @abstractmethod
    def format_tools(self, tools: List[Dict]) -> Any:
        """Format tools for this provider's API."""
        pass

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage.

        Can be overridden by specific providers.
        """
        # Default pricing (can be overridden)
        return (input_tokens / 1000) * 0.003 + (output_tokens / 1000) * 0.015


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible API provider (works with custom endpoints like BigModel)."""

    PRICING = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "gpt-3.5-turbo-16k": {"input": 0.0005, "output": 0.0015},
        "glm-4.7": {"input": 0.015, "output": 0.03},
        "glm-4-plus": {"input": 0.015, "output": 0.03},
    }

    def __init__(self, config: BioAgentConfig):
        super().__init__(config)
        self._client = None

    def _get_client(self):
        """Lazy initialization of the OpenAI client."""
        if self._client is None:
            try:
                import openai
                kwargs = {"api_key": self.config.api_key}
                if self.config.base_url:
                    kwargs["base_url"] = self.config.base_url
                self._client = openai.AsyncOpenAI(**kwargs)
            except ImportError:
                raise ImportError(
                    "openai package is required. Install with: pip install openai"
                )
        return self._client

    def format_tools(self, tools: List[Dict]) -> Any:
        """Format tools for OpenAI API."""
        # OpenAI uses "functions" instead of "tools"
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("input_schema", tool.get("parameters", {}))
                }
            }
            for tool in tools
        ]

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on OpenAI pricing."""
        # Get pricing for model or use defaults
        pricing = self.PRICING.get(
            self.config.model,
            {"input": 0.003, "output": 0.015}
        )
        return (input_tokens / 1000) * pricing["input"] + (output_tokens / 1000) * pricing["output"]

    async def call(
        self,
        messages: List[Message],
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> LLMResponse:
        """Call OpenAI-compatible API."""
        start_time = time.time()

        client = self._get_client()

        # Format messages for OpenAI
        openai_messages = []
        for msg in messages:
            if msg.role == "tool":
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content
                })
            else:
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # Prepare request parameters
        params = {
            "model": self.config.model,
            "messages": openai_messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }

        if tools:
            params["tools"] = self.format_tools(tools)

        try:
            response = await client.chat.completions.create(**params)
            duration_ms = (time.time() - start_time) * 1000

            # Parse response
            message = response.choices[0].message
            content = message.content
            tool_calls = []

            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tc in message.tool_calls:
                    # Parse arguments from JSON string
                    args_dict = {}
                    if isinstance(tc.function.arguments, str):
                        try:
                            args_dict = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            args_dict = {}
                    else:
                        args_dict = tc.function.arguments

                    tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=args_dict
                    ))

            # Get usage and calculate cost
            usage = response.usage
            cost = self.calculate_cost(
                usage.prompt_tokens,
                usage.completion_tokens
            )

            return LLMResponse(
                content=content,
                tool_calls=tool_calls if tool_calls else None,
                model=response.model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                total_tokens=usage.prompt_tokens + usage.completion_tokens,
                cost=cost,
                duration_ms=duration_ms,
                stop_reason=response.choices[0].finish_reason
            )

        except Exception as e:
            raise RuntimeError(f"Error calling OpenAI API: {e}")


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

    PRICING = {
        "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
        "claude-3-5-haiku-20241022": {"input": 0.0008, "output": 0.004},
    }

    def __init__(self, config: BioAgentConfig):
        super().__init__(config)
        self._client = None

    def _get_client(self):
        """Lazy initialization of the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                kwargs = {"api_key": self.config.api_key}
                if self.config.base_url:
                    kwargs["base_url"] = self.config.base_url
                self._client = anthropic.AsyncAnthropic(**kwargs)
            except ImportError:
                raise ImportError(
                    "anthropic package is required. Install with: pip install anthropic"
                )
        return self._client

    def format_tools(self, tools: List[Dict]) -> Any:
        """Format tools for Anthropic API."""
        # Anthropic uses the same format as OpenAI tools
        return tools if tools else None

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on Claude pricing."""
        # Get pricing for model or use defaults
        pricing = self.PRICING.get(
            self.config.model,
            {"input": 0.003, "output": 0.015}
        )
        return (input_tokens / 1000) * pricing["input"] + (output_tokens / 1000) * pricing["output"]

    async def call(
        self,
        messages: List[Message],
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> LLMResponse:
        """Call Anthropic Claude API."""
        start_time = time.time()

        client = self._get_client()

        # Format messages for Anthropic
        anthropic_messages = []
        for msg in messages:
            if msg.role == "tool":
                anthropic_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content
                        }
                    ]
                })
            else:
                anthropic_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # Prepare request parameters
        params = {
            "model": self.config.model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }

        if tools:
            params["tools"] = self.format_tools(tools)

        try:
            response = await client.messages.create(**params)
            duration_ms = (time.time() - start_time) * 1000

            # Parse response
            content = response.content
            text_content = []
            tool_calls = []

            for block in content:
                if block.type == "text":
                    text_content.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append(ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input
                    ))

            # Get usage and calculate cost
            usage = response.usage
            cost = self.calculate_cost(
                usage.input_tokens,
                usage.output_tokens
            )

            return LLMResponse(
                content="\n".join(text_content) if text_content else None,
                tool_calls=tool_calls if tool_calls else None,
                model=response.model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.input_tokens + usage.output_tokens,
                cost=cost,
                duration_ms=duration_ms,
                stop_reason=response.stop_reason
            )

        except Exception as e:
            raise RuntimeError(f"Error calling Anthropic API: {e}")


def get_llm_provider(config: BioAgentConfig) -> LLMProvider:
    """Factory function to get the appropriate LLM provider."""
    model_lower = config.model.lower()

    # Check for custom base URL (indicates OpenAI-compatible API)
    if config.base_url:
        return OpenAIProvider(config)

    # Otherwise, use model name to determine provider
    if "claude" in model_lower or "anthropic" in model_lower:
        return AnthropicProvider(config)
    elif "gpt" in model_lower or "openai" in model_lower or "glm" in model_lower:
        return OpenAIProvider(config)

    raise ValueError(f"Unsupported model: {config.model}. Supported: Claude, GPT, and GLM models")
