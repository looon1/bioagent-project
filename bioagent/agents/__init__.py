"""
Multi-agent team module for BioAgent.

Provides team-based agent composition patterns for multi-agent workflows.
"""

from bioagent.agents.team import (
    Team,
    SequentialTeam,
    HierarchicalTeam,
    AgentAsToolTeam,
    SwarmTeam
)

__all__ = [
    "Team",
    "SequentialTeam",
    "HierarchicalTeam",
    "AgentAsToolTeam",
    "SwarmTeam"
]
