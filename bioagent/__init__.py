"""
BioAgent - Biomedical AI Agent Framework

A minimal, modular framework for building AI agents specialized in
biomedical research and analysis.
"""

__version__ = "0.2.0"
__author__ = "fzh_hblab"

from bioagent.agent import Agent
from bioagent.config import BioAgentConfig
from bioagent.state import AgentState

# Import teams if available
try:
    from bioagent.agents import Team, SequentialTeam, HierarchicalTeam
    __all__ = ["Agent", "BioAgentConfig", "AgentState", "Team", "SequentialTeam", "HierarchicalTeam"]
except ImportError:
    __all__ = ["Agent", "BioAgentConfig", "AgentState"]
