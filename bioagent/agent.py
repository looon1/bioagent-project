"""
Main Agent class for BioAgent.

Implements the core agent execution loop with tool calling.
"""

import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from bioagent.config import BioAgentConfig
from bioagent.state import AgentState, AgentStatus, ToolResult, LLMCall, Message
from bioagent.llm import get_llm_provider, Message as LLMMessage, LLMResponse
from bioagent.tools.registry import ToolRegistry
from bioagent.tools.loader import ToolLoader
from bioagent.tools.adapter import ToolAdapter, BiomniToolAdapter
from bioagent.tools.base import ToolInfo
from bioagent.observability import Logger, Metrics, CostTracker


class Agent:
    """
    Main BioAgent class.

    Implements a ReAct-style agent with tool calling capabilities.
    """

    def __init__(
        self,
        config: Optional[BioAgentConfig] = None,
        system_prompt: Optional[str] = None
    ):
        """
        Initialize the agent.

        Args:
            config: Configuration for the agent (uses defaults if not provided)
            system_prompt: Optional custom system prompt
        """
        # Configuration
        self.config = config or BioAgentConfig.from_env()
        self.config.validate()

        # Observability
        self.logger = Logger("bioagent", self.config)
        self.metrics = Metrics() if self.config.enable_metrics else None
        self.cost_tracker = CostTracker() if self.config.enable_cost_tracking else None

        # State
        self.session_id = str(uuid.uuid4())[:8]
        self.state = AgentState()
        self.state.metadata["session_id"] = self.session_id

        # System prompt
        if system_prompt is None:
            from bioagent.prompts import SYSTEM_PROMPT
            self.system_prompt = SYSTEM_PROMPT
        else:
            self.system_prompt = system_prompt

        # Tool system
        self.tool_registry = ToolRegistry()
        self.loader = ToolLoader(self.tool_registry)
        self.tool_adapter: Optional[ToolAdapter] = None
        self._load_tools()

        # LLM Provider
        self.llm = get_llm_provider(self.config)

        self.logger.info(
            f"Agent initialized",
            session_id=self.session_id,
            model=self.config.model,
            tools=len(self.tool_registry)
        )

    def _load_tools(self) -> None:
        """Load all available tools."""
        # Load core tools from package
        try:
            self.tool_registry.register_from_package("bioagent.tools.core")
            self.logger.debug(
                f"Loaded core tools: {self.tool_registry.list_tool_names()}"
            )
        except Exception as e:
            self.logger.warning(f"Failed to load core tools: {e}")

        # Load external tools from Biomni if enabled
        if self.config.enable_biomni_tools:
            self._load_biomni_tools()

    def _load_biomni_tools(self) -> None:
        """Load Biomni tools via adapter."""
        try:
            self.tool_adapter = BiomniToolAdapter(
                registry=self.tool_registry,
                logger=self.logger,
                biomni_path=self.config.biomni_path
            )

            count = self.tool_adapter.register_all(
                domains=self.config.biomni_domains
            )

            self.logger.info(
                f"Loaded {count} Biomni tools from "
                f"{len(self.tool_adapter.list_available_domains())} domains"
            )

            # Log available domains
            domains = self.tool_adapter.list_available_domains()
            self.logger.debug(f"Available domains: {domains}")

        except Exception as e:
            self.logger.warning(f"Failed to load Biomni tools: {e}")
            self.tool_adapter = None

    def register_tool(self, tool_func) -> None:
        """
        Register a custom tool to the registry.

        Args:
            tool_func: A function decorated with @tool
        """
        self.tool_registry.register(tool_func)
        self.logger.debug(f"Registered custom tool: {tool_func.__name__}")

    def enable_tool_domain(self, domain: str) -> int:
        """
        Enable all tools in a domain.

        Args:
            domain: Domain name to enable

        Returns:
            Number of tools enabled
        """
        if self.tool_adapter:
            count = self.tool_adapter.enable_domain(domain)
            self.logger.info(f"Enabled {count} tools in domain '{domain}'")
            return count
        return 0

    def disable_tool_domain(self, domain: str) -> int:
        """
        Disable all tools in a domain.

        Args:
            domain: Domain name to disable

        Returns:
            Number of tools disabled
        """
        if self.tool_adapter:
            count = self.tool_adapter.disable_domain(domain)
            self.logger.info(f"Disabled {count} tools in domain '{domain}'")
            return count
        return 0

    def list_tool_domains(self) -> List[str]:
        """
        List all available tool domains.

        Returns:
            List of domain names
        """
        if self.tool_adapter:
            return self.tool_adapter.list_available_domains()
        return []

    def get_enabled_tools(self, domain: Optional[str] = None) -> List[ToolInfo]:
        """
        Get list of enabled tools.

        Args:
            domain: Optional filter by domain

        Returns:
            List of enabled ToolInfo objects
        """
        if self.tool_adapter:
            return self.tool_adapter.get_enabled_tools(domain=domain)
        return self.tool_registry.list_tools(domain=domain)

    async def execute(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute a query through the agent.

        Args:
            query: The user query to process
            context: Optional context variables

        Returns:
            The agent's response to the query
        """
        self.state.status = AgentStatus.THINKING
        self.state.context_variables.update(context or {})

        # Add user message to history
        self.state.add_message("user", query)

        self.logger.log_state_transition("idle", "thinking", session_id=self.session_id)

        # Build messages for LLM
        messages = self._build_messages(query)

        iteration = 0
        max_iterations = self.config.max_tool_iterations

        while iteration < max_iterations:
            iteration += 1

            # Call LLM
            self.state.status = AgentStatus.THINKING
            tools_def = self.tool_registry.to_openai_format()

            try:
                response = await self.llm.call(
                    messages=messages,
                    tools=tools_def
                )
            except Exception as e:
                self.logger.error(f"LLM call failed: {e}", session_id=self.session_id)
                return f"Error: Failed to process query - {str(e)}"

            # Record metrics
            if self.metrics:
                self.metrics.record_llm_call(
                    model=response.model or self.config.model,
                    tokens=response.total_tokens,
                    duration=response.duration_ms
                )
            if self.cost_tracker:
                self.cost_tracker.record(
                    model=response.model or self.config.model,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens
                )

            # Add assistant response to history
            if response.content:
                self.state.add_message("assistant", response.content)

            # Log the call
            self.logger.log_llm_call(
                model=response.model or self.config.model,
                tokens={
                    "input": response.input_tokens,
                    "output": response.output_tokens,
                    "total": response.total_tokens
                },
                cost=response.cost,
                duration=response.duration_ms,
                session_id=self.session_id
            )

            # Record LLM call in state
            llm_call = LLMCall(
                model=response.model or self.config.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                total_tokens=response.total_tokens,
                cost=response.cost,
                duration_ms=response.duration_ms,
                tool_calls=[tc.name for tc in (response.tool_calls or [])]
            )
            self.state.add_llm_call(llm_call)

            # Check if tools were requested
            if not response.tool_calls:
                # No tools, return the content
                self.state.status = AgentStatus.COMPLETED
                return response.content or "No response generated."

            # Execute tools
            self.state.status = AgentStatus.EXECUTING_TOOL

            for tool_call in response.tool_calls:
                # Add tool call to messages
                messages.append(LLMMessage(
                    role="user",
                    content=f"Executing {tool_call.name}",
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    tool_args=tool_call.arguments
                ))

                # Execute the tool
                start_time = time.time()
                try:
                    result = await self.tool_registry.execute(
                        tool_call.name,
                        tool_call.arguments
                    )
                    success = True
                    error = None
                except Exception as e:
                    result = {"error": str(e)}
                    success = False
                    error = str(e)

                duration = (time.time() - start_time) * 1000

                # Record tool result
                tool_result = ToolResult(
                    tool_name=tool_call.name,
                    success=success,
                    result=result,
                    error=error,
                    duration_ms=duration
                )
                self.state.add_tool_result(tool_result)

                # Log tool call
                if self.metrics:
                    self.metrics.record_tool_call(
                        tool=tool_call.name,
                        duration=duration,
                        success=success
                    )
                if self.cost_tracker:
                    pass  # Tools don't have direct cost in Phase 1

                self.logger.log_tool_call(
                    tool_name=tool_call.name,
                    args=tool_call.arguments,
                    success=success,
                    duration=duration,
                    error=error,
                    session_id=self.session_id
                )

                # Add tool result to messages
                result_str = str(result)
                if isinstance(result, dict) and "error" in result:
                    result_str = f"Error: {result['error']}"

                messages.append(LLMMessage(
                    role="tool",
                    content=result_str,
                    tool_call_id=tool_call.id
                ))

        # Max iterations reached
        return "I reached the maximum number of tool iterations. Please provide more specific instructions."

    def _build_messages(self, query: str) -> List[LLMMessage]:
        """Build the initial message list for LLM call."""
        messages = [
            LLMMessage(role="system", content=self.system_prompt),
        ]

        # Add recent conversation history
        recent_messages = self.state.messages[-(self.config.max_message_history-1):]
        for msg in recent_messages:
            messages.append(LLMMessage(
                role=msg.role,
                content=msg.content
            ))

        return messages

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session."""
        return {
            "session_id": self.session_id,
            "state": {
                "status": self.state.status.value,
                "message_count": len(self.state.messages),
                "tool_calls": len(self.state.tool_results),
                "llm_calls": len(self.state.llm_calls)
            },
            "costs": self.state.get_cost_summary(),
            "metrics": self.metrics.get_summary() if self.metrics else None
        }

    def reset(self) -> None:
        """Reset the agent state for a new session."""
        self.state = AgentState()
        self.state.metadata["session_id"] = str(uuid.uuid4())[:8]
        self.session_id = self.state.metadata["session_id"]

        if self.metrics:
            self.metrics.reset()
        if self.cost_tracker:
            self.cost_tracker.reset()

        self.logger.info("Agent state reset", session_id=self.session_id)
