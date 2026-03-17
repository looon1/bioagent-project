"""
Autonomous Agent implementation with idle polling and auto-task claiming.

Implements self-organizing agents that can:
- Poll for new work during idle periods
- Automatically claim tasks from the team board
- Maintain their own status (working/idle/shutdown)
- Coordinate with other agents via message bus
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from bioagent.config import BioAgentConfig
from bioagent.team.protocol import MessageBus, TeamProtocol, MessageType

if TYPE_CHECKING:
    from bioagent.agent import Agent
    from bioagent.tasks.manager import TaskManager


class AgentStatus(str, Enum):
    """Status of an autonomous agent."""
    INITIALIZING = "initializing"
    WORKING = "working"
    IDLE = "idle"
    SHUTDOWN = "shutdown"


@dataclass
class AutonomousConfig:
    """Configuration for autonomous agent behavior."""
    poll_interval: float = 5.0  # Seconds between polls
    idle_timeout: float = 60.0  # Seconds before shutdown
    max_idle_cycles: int = 10  # Max idle cycles before shutdown
    auto_claim_tasks: bool = True  # Automatically claim unassigned tasks


class AutonomousAgent:
    """
    Autonomous agent with self-organizing capabilities.

    Runs in a continuous loop with work/idle phases:
    - Work phase: Execute assigned tasks
    - Idle phase: Poll for new work, claim tasks if available
    - Shutdown: Terminate after idle timeout or explicit shutdown request
    """

    def __init__(
        self,
        agent: "Agent",
        name: str,
        role: str,
        team_name: str,
        message_bus: MessageBus,
        task_manager: Optional["TaskManager"] = None,
        config: Optional[AutonomousConfig] = None,
    ):
        """
        Initialize autonomous agent.

        Args:
            agent: Underlying BioAgent instance
            name: Agent name
            role: Agent role (e.g., "researcher", "analyzer")
            team_name: Name of the team
            message_bus: Message bus for team communication
            task_manager: Task manager for claiming tasks
            config: Autonomous behavior configuration
        """
        self.agent = agent
        self.name = name
        self.role = role
        self.team_name = team_name
        self.message_bus = message_bus
        self.task_manager = task_manager
        self.config = config or AutonomousConfig()

        # State
        self.status = AgentStatus.INITIALIZING
        self.current_task: Optional[str] = None
        self.idle_cycles = 0
        self.last_activity = time.time()

        # Team protocol
        self.protocol = TeamProtocol(message_bus, name, agent.logger if agent else None)

        # Task for running the autonomous loop
        self._loop_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the autonomous agent loop."""
        if self._loop_task is not None and not self._loop_task.done():
            raise RuntimeError("Autonomous agent is already running")

        self.status = AgentStatus.WORKING
        self._shutdown_event.clear()
        self._loop_task = asyncio.create_task(self._autonomous_loop())

        if self.agent and self.agent.logger:
            self.agent.logger.info(
                "Autonomous agent started",
                agent_name=self.name,
                role=self.role,
                team=self.team_name,
            )

    async def stop(self, graceful: bool = True) -> None:
        """
        Stop the autonomous agent.

        Args:
            graceful: If True, complete current task before stopping
        """
        if self._loop_task is None or self._loop_task.done():
            return

        self._shutdown_event.set()

        if graceful and self.current_task:
            # Wait for current task to complete
            try:
                await asyncio.wait_for(
                    self._loop_task, timeout=self.config.idle_timeout
                )
            except asyncio.TimeoutError:
                # Force shutdown
                self._loop_task.cancel()
        else:
            self._loop_task.cancel()

        self.status = AgentStatus.SHUTDOWN

        if self.agent and self.agent.logger:
            self.agent.logger.info(
                "Autonomous agent stopped",
                agent_name=self.name,
                graceful=graceful,
            )

    async def _autonomous_loop(self) -> None:
        """Main autonomous loop."""
        try:
            while not self._shutdown_event.is_set():
                # Check for shutdown request via protocol
                inbox = self.message_bus.read_inbox(self.name)
                await self._process_messages(inbox)

                # Check for explicit shutdown
                if self.protocol.shutdown_requested:
                    await self._handle_shutdown_request()
                    break

                # Execute work phase
                await self._work_phase()

                # Execute idle phase
                work_found = await self._idle_phase()

                if not work_found:
                    self.idle_cycles += 1

                    # Check for idle timeout
                    if self.idle_cycles >= self.config.max_idle_cycles:
                        if self.agent and self.agent.logger:
                            self.agent.logger.info(
                                "Idle timeout reached, shutting down",
                                agent_name=self.name,
                                idle_cycles=self.idle_cycles,
                            )
                        break
                else:
                    self.idle_cycles = 0
                    self.status = AgentStatus.WORKING

        except asyncio.CancelledError:
            pass
        finally:
            self.status = AgentStatus.SHUTDOWN

    async def _process_messages(self, messages) -> None:
        """
        Process incoming messages.

        Args:
            messages: List of messages from inbox
        """
        for msg in messages:
            # Handle protocol messages
            await self.protocol.handle_protocol_message(msg)

            # Handle task-related messages
            if msg.type == MessageType.TASK_CLAIMED:
                await self._handle_task_claimed(msg)
            elif msg.type == MessageType.TASK_COMPLETED:
                await self._handle_task_completed(msg)
            elif msg.type == MessageType.TASK_FAILED:
                await self._handle_task_failed(msg)

    async def _work_phase(self) -> None:
        """
        Execute work phase - process current task if any.

        This is where the agent does its actual work.
        In a real implementation, this would:
        1. Check if there's a current task
        2. Execute the task using the agent
        3. Report completion
        """
        if self.current_task:
            # Work on current task
            self.last_activity = time.time()

            # In a real implementation, we'd execute the task here
            # For now, just mark as complete after a short delay
            await asyncio.sleep(0.1)

            # Simulate task completion
            if self.task_manager:
                self.task_manager.update(self.current_task, status="completed")
                self.current_task = None

    async def _idle_phase(self) -> bool:
        """
        Execute idle phase - poll for new work.

        Args:
            Returns True if work was found, False if still idle

        Returns:
            Boolean indicating if work was found
        """
        # Poll for messages
        inbox = self.message_bus.read_inbox(self.name)
        if inbox:
            await self._process_messages(inbox)
            return True

        # Check if we should claim a task
        if self.config.auto_claim_tasks and self.task_manager:
            task = self._find_claimable_task()
            if task:
                await self._claim_task(task["id"])
                return True

        # Wait for poll interval
        self.status = AgentStatus.IDLE
        try:
            await asyncio.wait_for(
                self._shutdown_event.wait(),
                timeout=self.config.poll_interval,
            )
        except asyncio.TimeoutError:
            pass

        return False

    def _find_claimable_task(self) -> Optional[dict]:
        """
        Find a task that this agent can claim.

        Args:
            Returns task dict or None if no claimable task

        Returns:
            Task dictionary or None
        """
        if not self.task_manager:
            return None

        # Get pending tasks with no owner
        pending = self.task_manager.list_tasks(status="pending")

        # Filter tasks suitable for this agent's role
        suitable_tasks = [
            t for t in pending
            if not t.get("owner") or t.get("owner") == ""
        ]

        # Return the highest priority task
        if suitable_tasks:
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            suitable_tasks.sort(
                key=lambda t: priority_order.get(t.get("priority", "medium"), 2)
            )
            return suitable_tasks[0]

        return None

    async def _claim_task(self, task_id: str) -> None:
        """
        Claim a task.

        Args:
            task_id: ID of task to claim
        """
        if self.task_manager:
            self.task_manager.update(task_id, status="in_progress")
            self.current_task = task_id
            self.idle_cycles = 0

            # Notify team
            self.message_bus.send(
                sender=self.name,
                to="team",
                content=f"Claimed task {task_id}",
                msg_type=MessageType.TASK_CLAIMED,
                extra={"task_id": task_id},
            )

            if self.agent and self.agent.logger:
                self.agent.logger.info(
                    "Task claimed",
                    agent_name=self.name,
                    task_id=task_id,
                )

    async def _handle_task_claimed(self, msg) -> None:
        """Handle notification that another agent claimed a task."""
        task_id = msg.extra.get("task_id")
        if task_id and self.current_task == task_id and msg.from_agent != self.name:
            # Another agent claimed our task, release it
            if self.task_manager:
                self.task_manager.update(task_id, owner=msg.from_agent)
                self.current_task = None

    async def _handle_task_completed(self, msg) -> None:
        """Handle notification that a task was completed."""
        if self.current_task == msg.extra.get("task_id"):
            self.current_task = None

    async def _handle_task_failed(self, msg) -> None:
        """Handle notification that a task failed."""
        if self.current_task == msg.extra.get("task_id"):
            # Could retry or re-claim
            self.current_task = None

    async def _handle_shutdown_request(self) -> None:
        """Handle a shutdown request from the team."""
        # Notify team that we're shutting down
        self.message_bus.send(
            sender=self.name,
            to="team",
            content="Shutting down",
            msg_type=MessageType.SHUTDOWN_RESPONSE,
        )

        if self.current_task and self.task_manager:
            # Release current task
            self.task_manager.update(self.current_task, owner="", status="pending")
            self.current_task = None

    def get_status(self) -> dict:
        """
        Get current status of the autonomous agent.

        Returns:
            Dictionary with status information
        """
        return {
            "name": self.name,
            "role": self.role,
            "team": self.team_name,
            "status": self.status.value,
            "current_task": self.current_task,
            "idle_cycles": self.idle_cycles,
            "last_activity": self.last_activity,
        }

    def reset_idle(self) -> None:
        """Reset idle cycle counter."""
        self.idle_cycles = 0
        self.last_activity = time.time()


class AutonomousTeam:
    """
    Team of autonomous agents with self-organizing capabilities.

    Manages a collection of autonomous agents and provides
    team-level coordination.
    """

    def __init__(
        self,
        team_name: str,
        work_dir: Path,
        config: BioAgentConfig,
    ):
        """
        Initialize autonomous team.

        Args:
            team_name: Name of the team
            work_dir: Working directory for team data
            config: BioAgent configuration
        """
        self.team_name = team_name
        self.work_dir = work_dir
        self.config = config

        # Communication
        self.inbox_dir = work_dir / f".team_{team_name}" / "inbox"
        self.message_bus = MessageBus(self.inbox_dir)

        # Team members
        self.agents: Dict[str, AutonomousAgent] = {}

        # Import here to avoid circular
        from bioagent.tasks.manager import TaskManager

        self.task_manager = TaskManager(
            work_dir / f".team_{team_name}" / "tasks",
            config.logger if hasattr(config, "logger") else None,
        )

    async def spawn_agent(
        self,
        name: str,
        role: str,
        autonomous_config: Optional[AutonomousConfig] = None,
    ) -> AutonomousAgent:
        """
        Spawn and start a new autonomous agent.

        Args:
            name: Agent name
            role: Agent role
            autonomous_config: Optional custom config

        Returns:
            The created autonomous agent
        """
        # Create underlying BioAgent
        from bioagent.agent import Agent

        agent = Agent(config=self.config)

        # Create autonomous wrapper
        autonomous = AutonomousAgent(
            agent=agent,
            name=name,
            role=role,
            team_name=self.team_name,
            message_bus=self.message_bus,
            task_manager=self.task_manager,
            config=autonomous_config,
        )

        # Start the agent
        await autonomous.start()

        # Register in team
        self.agents[name] = autonomous

        return autonomous

    async def shutdown_agent(self, name: str, graceful: bool = True) -> None:
        """
        Shutdown a team member.

        Args:
            name: Agent name to shutdown
            graceful: If True, complete current task
        """
        if name in self.agents:
            await self.agents[name].stop(graceful=graceful)
            del self.agents[name]

    async def shutdown_all(self, graceful: bool = True) -> None:
        """
        Shutdown all team members.

        Args:
            graceful: If True, complete current tasks
        """
        for name, agent in list(self.agents.items()):
            await self.shutdown_agent(name, graceful=graceful)

    def get_team_status(self) -> dict:
        """
        Get status of all team members.

        Returns:
            Dictionary with team status
        """
        return {
            "team_name": self.team_name,
            "member_count": len(self.agents),
            "members": {
                name: agent.get_status()
                for name, agent in self.agents.items()
            },
            "tasks": self.task_manager.get_summary() if self.task_manager else {},
        }
