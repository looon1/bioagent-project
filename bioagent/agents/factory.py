"""
Simple agent factory for multi-agent delegation.
"""

from typing import Optional, List, TYPE_CHECKING
from bioagent.config import BioAgentConfig
from bioagent.agents.analyzer import TaskComplexityAnalyzer

if TYPE_CHECKING:
    from bioagent.agent import Agent
    from bioagent.agents.team import Team, HierarchicalTeam


class SimpleAgentFactory:
    """Simple factory for multi-agent teams."""

    def __init__(self, config: BioAgentConfig, logger=None):
        self.config = config
        self.logger = logger
        self.analyzer = TaskComplexityAnalyzer(config)
        self._agent_pool: List["Agent"] = []

    def should_delegate(self, query: str) -> bool:
        """Check if query should be delegated to multiple agents."""
        return self.analyzer.should_use_multi_agent(query)

    def create_multi_agent_team(self) -> "Team":
        """Create a simple hierarchical team for multi-agent processing."""
        # Import here to avoid circular imports
        from bioagent.agent import Agent
        from bioagent.agents.team import HierarchicalTeam

        # Create 2-3 agents with the same configuration
        agent1 = Agent(self.config)
        agent2 = Agent(self.config)
        agent3 = Agent(self.config)

        # Use agent2 as supervisor, agent1 and agent3 as workers
        team = HierarchicalTeam(
            supervisor=agent2,
            subagents=[agent1, agent3],
            delegation_prompt=(
                "You are coordinating multiple agents. "
                "Delegate tasks to other agents when appropriate."
            )
        )

        self._agent_pool = [agent1, agent2, agent3]
        return team

    def cleanup(self):
        """Clean up agent pool."""
        self._agent_pool.clear()
