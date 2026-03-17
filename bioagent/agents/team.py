"""
Team-based agent composition patterns.

Provides multi-agent collaboration patterns inspired by PantheonOS architecture.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union

from bioagent.agent import Agent


class Team(ABC):
    """
    Abstract base class for agent teams.

    Teams coordinate multiple agents to accomplish complex tasks
    through various composition patterns.
    """

    def __init__(self, agents: List[Agent]):
        """
        Initialize the team.

        Args:
            agents: List of agents in this team
        """
        self.agents = agents
        self._agent_map: Dict[str, Agent] = {
            agent.session_id: agent for agent in agents
        }

    @abstractmethod
    async def execute(self, query: str, **kwargs) -> str:
        """
        Execute a query through the team.

        Args:
            query: The user query to process
            **kwargs: Additional arguments for execution

        Returns:
            The team's response to the query
        """
        pass

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """
        Get an agent by its session ID.

        Args:
            agent_id: The session ID of the agent

        Returns:
            The Agent object or None if not found
        """
        return self._agent_map.get(agent_id)

    def list_agents(self) -> List[str]:
        """
        List all agent session IDs in this team.

        Returns:
            List of agent session IDs
        """
        return list(self._agent_map.keys())


class SequentialTeam(Team):
    """
    Sequential team pattern - agents execute in order.

    Each agent processes the output of the previous agent,
    creating a pipeline of processing steps.
    """

    def __init__(
        self,
        agents: List[Agent],
        connect_prompt: str = "Next:"
    ):
        """
        Initialize the sequential team.

        Args:
            agents: List of agents to execute in sequence
            connect_prompt: Message to pass between agents
        """
        super().__init__(agents)
        self.connect_prompt = connect_prompt

    async def execute(self, query: str, **kwargs) -> str:
        """
        Execute query sequentially through all agents.

        Args:
            query: The user query to process
            **kwargs: Additional arguments (not used in sequential mode)

        Returns:
            Final result after all agents have processed
        """
        result = query

        for i, agent in enumerate(self.agents):
            # Execute agent
            response = await agent.execute(result)

            # Pass result to next agent with connect prompt
            if i < len(self.agents) - 1:
                result = f"{self.connect_prompt} {response}"
            else:
                result = response

        return result

    async def execute_with_context(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute sequentially with shared context.

        Args:
            query: The user query to process
            context: Optional shared context dictionary

        Returns:
            Final result after all agents have processed
        """
        result = query
        shared_context = context or {}

        for i, agent in enumerate(self.agents):
            # Execute agent with shared context
            response = await agent.execute(result, context=shared_context)

            # Pass result to next agent
            if i < len(self.agents) - 1:
                result = f"{self.connect_prompt} {response}"
            else:
                result = response

        return result


class HierarchicalTeam(Team):
    """
    Hierarchical team pattern - supervisor delegates to sub-agents.

    A supervisor agent analyzes the task and delegates to specialized
    sub-agents based on task requirements.
    """

    def __init__(
        self,
        supervisor: Agent,
        subagents: List[Agent],
        delegation_prompt: str = None
    ):
        """
        Initialize the hierarchical team.

        Args:
            supervisor: The managing/supervisor agent
            subagents: List of specialized sub-agents
            delegation_prompt: Optional custom prompt for delegation
        """
        all_agents = [supervisor] + subagents
        super().__init__(all_agents)

        self.supervisor = supervisor
        self.subagents = subagents
        self.delegation_prompt = delegation_prompt or (
            "You are a supervisor. Analyze the task and delegate it "
            "to the most appropriate sub-agent. "
            "Available sub-agents: {agent_ids}. "
            "Your response should include the sub-agent ID to delegate to."
        )

    async def execute(self, query: str, **kwargs) -> str:
        """
        Execute query through hierarchical delegation.

        Args:
            query: The user query to process
            **kwargs: Additional arguments (not used in hierarchical mode)

        Returns:
            Result from the delegated agent or supervisor
        """
        # Build agent list for supervisor
        agent_list = "\n".join([
            f"- {agent.session_id}: {agent.__class__.__name__}"
            for agent in self.subagents
        ])

        # Ask supervisor to analyze and delegate
        supervisor_prompt = self.delegation_prompt.format(agent_ids=agent_list)
        decision_query = f"{supervisor_prompt}\n\nTask: {query}"

        decision = await self.supervisor.execute(decision_query)

        # Parse decision for delegation
        target_agent_id = self._parse_delegation(decision)

        if target_agent_id and target_agent_id in self._agent_map:
            # Delegate to sub-agent
            target_agent = self._agent_map[target_agent_id]
            result = await target_agent.execute(query)
            return result
        else:
            # No delegation, return supervisor's analysis
            return decision

    def _parse_delegation(self, decision: str) -> Optional[str]:
        """
        Parse supervisor's decision for target agent ID.

        Args:
            decision: The supervisor's response

        Returns:
            Agent session ID or None if no delegation found
        """
        # Look for patterns like "delegate to agent: XYZ" or "assign to: XYZ"
        decision_lower = decision.lower()

        # Try to extract session ID from decision
        for agent_id in self._agent_map.keys():
            if agent_id in decision:
                return agent_id

        # Look for common delegation patterns
        if "delegate to" in decision_lower:
            # Extract after "delegate to"
            parts = decision_lower.split("delegate to")
            if len(parts) > 1:
                # Try to find an agent ID in the remaining text
                for agent_id in self._agent_map.keys():
                    if agent_id in parts[1]:
                        return agent_id

        return None

    async def execute_with_feedback(
        self,
        query: str,
        max_rounds: int = 3
    ) -> str:
        """
        Execute with supervisor-sub-agent feedback loop.

        Args:
            query: The user query to process
            max_rounds: Maximum number of delegation rounds

        Returns:
            Final result after feedback rounds
        """
        current_query = query

        for round_num in range(max_rounds):
            # Execute normal delegation
            result = await self.execute(current_query)

            # Check if supervisor wants another round
            if round_num < max_rounds - 1 and self._needs_feedback(result):
                # Ask supervisor to provide feedback for next round
                feedback = await self.supervisor.execute(
                    f"Review this result and provide feedback for improvement: {result}"
                )
                current_query = f"Task: {query}\nFeedback: {feedback}"
            else:
                return result

        return result

    def _needs_feedback(self, result: str) -> bool:
        """
        Check if result indicates need for another round.

        Args:
            result: The result to check

        Returns:
            True if another round is needed
        """
        # Look for patterns indicating incomplete results
        incomplete_patterns = [
            "incomplete",
            "needs more",
            "should try again",
            "feedback needed"
        ]

        result_lower = result.lower()
        return any(pattern in result_lower for pattern in incomplete_patterns)


class AgentAsToolTeam(Team):
    """
    Agent-as-tool pattern - sub-agents exposed as tools to leader.

    The leader agent can call sub-agents as if they were tools,
    enabling sophisticated multi-agent workflows.
    """

    def __init__(
        self,
        leader: Agent,
        subagents: List[Agent],
        tool_description_template: Optional[Callable] = None,
        agent_descriptions: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the agent-as-tool team.

        Args:
            leader: The main agent that coordinates sub-agents
            subagents: List of sub-agents available as tools
            tool_description_template: Optional function to generate tool descriptions
            agent_descriptions: Optional dict mapping agent IDs to descriptions
        """
        all_agents = [leader] + subagents
        super().__init__(all_agents)

        self.leader = leader
        self.subagents = subagents
        self.agent_descriptions = agent_descriptions or {}
        self._tool_results: Dict[str, Any] = {}

        # Register sub-agents as tools to the leader
        if agent_descriptions:
            self._register_subagents_as_tools_with_descriptions(agent_descriptions)
        else:
            self._register_subagents_as_tools(tool_description_template)

    def _register_subagents_as_tools(
        self,
        description_template: Optional[Callable] = None
    ) -> None:
        """
        Register each sub-agent as a tool callable by the leader.

        Args:
            description_template: Optional function to generate descriptions
        """
        from bioagent.tools.base import tool

        for subagent in self.subagents:
            agent_id = subagent.session_id

            # Generate tool description
            if description_template:
                description = description_template(subagent)
            else:
                description = (
                    f"Call sub-agent '{agent_id}' for specialized processing. "
                    f"Use this tool when tasks require specialized capabilities "
                    f"beyond the general agent."
                )

            # Create tool function
            @tool(domain="agent")
            async def call_sub_agent(instruction: str) -> str:
                """Call a sub-agent with an instruction."""
                result = await subagent.execute(instruction)
                # Store result for reference
                self._tool_results[agent_id] = result
                return result

            # Set tool metadata
            call_sub_agent.__name__ = f"agent_{agent_id}"
            call_sub_agent.__doc__ = description
            call_sub_agent._target_agent_id = agent_id

            # Register to leader's registry
            try:
                self.leader.tool_registry.register(call_sub_agent)
            except ValueError:
                # Tool already registered, skip
                continue

    def _register_subagents_as_tools_with_descriptions(
        self,
        descriptions: Dict[str, str]
    ) -> None:
        """
        Register each sub-agent as a tool with predefined descriptions.

        Args:
            descriptions: Dict mapping agent IDs to descriptions
        """
        from bioagent.tools.base import tool

        for subagent in self.subagents:
            agent_id = subagent.session_id

            # Use predefined description or fall back to default
            description = descriptions.get(agent_id, (
                f"Call sub-agent '{agent_id}' for specialized processing. "
                f"Use this tool when tasks require specialized capabilities "
                f"beyond the general agent."
            ))

            # Create tool function
            @tool(domain="agent")
            async def call_sub_agent(instruction: str) -> str:
                """Call a sub-agent with an instruction."""
                result = await subagent.execute(instruction)
                # Store result for reference
                self._tool_results[agent_id] = result
                return result

            # Set tool metadata
            call_sub_agent.__name__ = f"agent_{agent_id}"
            call_sub_agent.__doc__ = description
            call_sub_agent._target_agent_id = agent_id

            # Register to leader's registry
            try:
                self.leader.tool_registry.register(call_sub_agent)
            except ValueError:
                # Tool already registered, skip
                continue

    async def execute(self, query: str, **kwargs) -> str:
        """
        Execute query through leader with sub-agents as tools.

        Args:
            query: The user query to process
            **kwargs: Additional arguments

        Returns:
            Result from the leader agent
        """
        # Leader has sub-agents available as tools
        result = await self.leader.execute(query)
        return result

    def get_tool_results(self) -> Dict[str, Any]:
        """
        Get results from sub-agent tool calls.

        Returns:
            Dictionary mapping agent IDs to their results
        """
        return self._tool_results.copy()

    def clear_tool_results(self) -> None:
        """Clear stored tool results."""
        self._tool_results.clear()

    def list_agent_tools(self) -> Dict[str, str]:
        """
        List all agent tools registered to the leader.

        Returns:
            Dict mapping tool names to descriptions
        """
        tools = {}
        for tool_info in self.leader.tool_registry.list_tools(domain="agent"):
            tools[tool_info.name] = tool_info.description
        return tools


class SwarmTeam(Team):
    """
    Swarm team pattern - handoff-based execution with agent transfer.

    Agents can hand off to each other dynamically during execution,
    with memory maintaining active agent state.
    """

    def __init__(self, agents: List[Agent], initial_agent: Optional[Agent] = None):
        """
        Initialize the swarm team.

        Args:
            agents: List of agents that can participate in the swarm
            initial_agent: Optional initial active agent (defaults to first agent)
        """
        super().__init__(agents)
        self.active_agent = initial_agent or agents[0] if agents else None
        self._handoff_prompt = (
            "You are agent {agent_id}. You can hand off to another agent "
            "if needed. To hand off, say 'HANDOFF TO {agent_id}' "
            "with the context."
        )

    async def execute(self, query: str, **kwargs) -> str:
        """
        Execute query with potential agent handoffs.

        Args:
            query: The user query to process
            **kwargs: Additional arguments

        Returns:
            Result after final agent completes
        """
        if not self.active_agent:
            raise ValueError("No active agent in swarm team")

        # Inject handoff capability into active agent
        current_agent = self.active_agent
        current_query = query

        max_handoffs = 10
        handoff_count = 0

        while handoff_count < max_handoffs:
            # Execute with handoff prompt
            agent_prompt = self._handoff_prompt.format(
                agent_id=current_agent.session_id
            )
            augmented_query = f"{agent_prompt}\n\n{current_query}"

            result = await current_agent.execute(augmented_query)

            # Check for handoff
            handoff_target = self._parse_handoff(result)

            if handoff_target and handoff_target in self._agent_map:
                # Hand off to another agent
                current_agent = self._agent_map[handoff_target]
                current_query = f"Previous context: {result}"
                handoff_count += 1
            else:
                # No handoff, return result
                return result

        return result

    def _parse_handoff(self, result: str) -> Optional[str]:
        """
        Parse result for handoff command.

        Args:
            result: The agent's response

        Returns:
            Target agent ID or None if no handoff
        """
        result_upper = result.upper()

        # Look for "HANDOFF TO {agent_id}" pattern
        if "HANDOFF TO" in result_upper:
            parts = result_upper.split("HANDOFF TO")
            if len(parts) > 1:
                # Extract agent ID from remaining text
                remaining = parts[1].strip()
                for agent_id in self._agent_map.keys():
                    if agent_id.upper() in remaining:
                        return agent_id

        return None

    def set_active_agent(self, agent_id: str) -> bool:
        """
        Manually set the active agent.

        Args:
            agent_id: The session ID of the agent to activate

        Returns:
            True if agent was found and activated
        """
        if agent_id in self._agent_map:
            self.active_agent = self._agent_map[agent_id]
            return True
        return False
