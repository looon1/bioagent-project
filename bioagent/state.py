"""
State management for BioAgent.

Defines the core state structures used during agent execution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class AgentStatus(Enum):
    """Status of agent execution."""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING_TOOL = "executing_tool"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LLMCall:
    """Record of an LLM API call."""
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: List[str] = field(default_factory=list)


@dataclass
class Message:
    """A message in the conversation."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_call_id: Optional[str] = None
    tool_results: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentState:
    """Current state of the agent."""
    status: AgentStatus = AgentStatus.IDLE
    messages: List[Message] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    llm_calls: List[LLMCall] = field(default_factory=list)
    context_variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, **kwargs) -> None:
        """Add a message to the conversation history."""
        message = Message(role=role, content=content, **kwargs)
        self.messages.append(message)

    def add_tool_result(self, result: ToolResult) -> None:
        """Add a tool result to the state."""
        self.tool_results.append(result)

    def add_llm_call(self, call: LLMCall) -> None:
        """Add an LLM call record."""
        self.llm_calls.append(call)

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get summary of costs incurred."""
        total_cost = sum(call.cost for call in self.llm_calls)
        total_tokens = sum(call.total_tokens for call in self.llm_calls)
        total_input = sum(call.input_tokens for call in self.llm_calls)
        total_output = sum(call.output_tokens for call in self.llm_calls)

        return {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "input_tokens": total_input,
            "output_tokens": total_output,
            "llm_calls": len(self.llm_calls),
            "tool_calls": len(self.tool_results),
        }
