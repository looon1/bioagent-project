"""
Advanced Team Protocols for BioAgent.

Provides:
- MessageBus: JSONL-based inter-agent communication
- TeamProtocol: Request-response, shutdown, and plan approval protocols
- AutonomousAgent: Self-organizing agents with idle polling
- KanbanBoard: Visual task management
- TeamManager: Team state persistence and health checks
"""
from .protocol import MessageBus, TeamProtocol, MessageType
from .autonomous import AutonomousAgent, AgentStatus
from .kanban import KanbanBoard
from .discovery import TeamManager, HealthChecker

__all__ = [
    "MessageBus",
    "TeamProtocol",
    "MessageType",
    "AutonomousAgent",
    "AgentStatus",
    "KanbanBoard",
    "TeamManager",
    "HealthChecker",
]
