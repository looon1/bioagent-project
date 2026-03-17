"""
Team discovery and health management.

Implements:
- Teammate registration and discovery
- Team state persistence
- Health check monitoring
- Agent reconnection mechanisms
"""

import asyncio
import json
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from bioagent.team.protocol import MessageBus, MessageType


class TeamMemberStatus(str, Enum):
    """Status of a team member."""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    UNRESPONSIVE = "unresponsive"


@dataclass
class TeamMember:
    """Information about a team member."""
    name: str
    role: str
    status: TeamMemberStatus = TeamMemberStatus.OFFLINE
    last_seen: float = field(default_factory=time.time)
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    agent_name: str
    status: TeamMemberStatus
    response_time_ms: float
    last_seen: float
    error: Optional[str] = None


class TeamManager:
    """
    Manages team state, member registration, and persistence.

    Provides a persistent view of team composition and member status.
    """

    def __init__(self, team_dir: Path, logger=None):
        """
        Initialize team manager.

        Args:
            team_dir: Directory for team state files
            logger: Optional logger instance
        """
        self.dir = team_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger

        # State files
        self.config_path = self.dir / "team_config.json"
        self.members_path = self.dir / "members.json"

        # Team configuration
        self.config = self._load_config()
        self.team_name = self.config.get("team_name", "default_team")

        # Team members
        self.members: Dict[str, TeamMember] = {}
        self._load_members()

    def _load_config(self) -> Dict:
        """Load team configuration from file."""
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass
        return {"team_name": "default_team"}

    def _save_config(self) -> None:
        """Save team configuration to file."""
        with self.config_path.open("w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)

    def _load_members(self) -> None:
        """Load team members from file."""
        if self.members_path.exists():
            try:
                data = json.loads(self.members_path.read_text(encoding="utf-8"))
                for name, member_data in data.items():
                    self.members[name] = TeamMember(
                        name=name,
                        role=member_data.get("role", "member"),
                        status=TeamMemberStatus(
                            member_data.get("status", "offline")
                        ),
                        last_seen=member_data.get("last_seen", time.time()),
                        capabilities=member_data.get("capabilities", []),
                        metadata=member_data.get("metadata", {}),
                    )
            except (json.JSONDecodeError, IOError):
                pass

    def _save_members(self) -> None:
        """Save team members to file."""
        members_data = {}
        for name, member in self.members.items():
            members_data[name] = {
                "role": member.role,
                "status": member.status.value,
                "last_seen": member.last_seen,
                "capabilities": member.capabilities,
                "metadata": member.metadata,
            }

        with self.members_path.open("w", encoding="utf-8") as f:
            json.dump(members_data, f, indent=2)

    def get_team_name(self) -> str:
        """Get the team name."""
        return self.team_name

    def set_team_name(self, name: str) -> None:
        """Set the team name."""
        self.team_name = name
        self.config["team_name"] = name
        self._save_config()

    def register_member(
        self,
        name: str,
        role: str = "member",
        capabilities: List[str] = None,
        metadata: Dict = None,
    ) -> None:
        """
        Register a new team member.

        Args:
            name: Member name
            role: Member role
            capabilities: List of capabilities
            metadata: Additional metadata
        """
        member = TeamMember(
            name=name,
            role=role,
            status=TeamMemberStatus.ONLINE,
            capabilities=capabilities or [],
            metadata=metadata or {},
        )

        self.members[name] = member
        self._save_members()

        if self.logger:
            self.logger.info(
                "Team member registered",
                name=name,
                role=role,
                team=self.team_name,
            )

    def unregister_member(self, name: str) -> None:
        """
        Unregister a team member.

        Args:
            name: Member name to remove
        """
        if name in self.members:
            del self.members[name]
            self._save_members()

            if self.logger:
                self.logger.info(
                    "Team member unregistered",
                    name=name,
                    team=self.team_name,
                )

    def update_member_status(
        self,
        name: str,
        status: TeamMemberStatus,
        last_seen: Optional[float] = None,
    ) -> None:
        """
        Update a member's status.

        Args:
            name: Member name
            status: New status
            last_seen: Optional timestamp
        """
        if name in self.members:
            self.members[name].status = status
            if last_seen is not None:
                self.members[name].last_seen = last_seen
            else:
                self.members[name].last_seen = time.time()
            self._save_members()

    def get_member(self, name: str) -> Optional[TeamMember]:
        """
        Get information about a team member.

        Args:
            name: Member name

        Returns:
            TeamMember or None if not found
        """
        return self.members.get(name)

    def get_all_members(self) -> List[TeamMember]:
        """
        Get all team members.

        Returns:
            List of all TeamMember objects
        """
        return list(self.members.values())

    def get_members_by_role(self, role: str) -> List[TeamMember]:
        """
        Get members with a specific role.

        Args:
            role: Role to filter by

        Returns:
            List of TeamMember objects
        """
        return [m for m in self.members.values() if m.role == role]

    def get_members_by_capability(
        self, capability: str
    ) -> List[TeamMember]:
        """
        Get members with a specific capability.

        Args:
            capability: Capability to filter by

        Returns:
            List of TeamMember objects
        """
        return [
            m for m in self.members.values()
            if capability in m.capabilities
        ]

    def find_member_for_task(self, task_type: str) -> Optional[TeamMember]:
        """
        Find a suitable member for a task.

        Args:
            task_type: Type of task to match

        Returns:
            Best matching TeamMember or None
        """
        # Look for members with matching capability
        candidates = self.get_members_by_capability(task_type)

        if not candidates:
            # Fall back to any online member
            candidates = [
                m for m in self.members.values()
                if m.status == TeamMemberStatus.ONLINE
            ]

        # Return the least busy member
        if candidates:
            # Sort by last seen (prefer recently active)
            candidates.sort(key=lambda m: m.last_seen, reverse=True)
            return candidates[0]

        return None

    def get_team_summary(self) -> Dict:
        """
        Get team summary.

        Returns:
            Dictionary with team information
        """
        status_counts = {s.value: 0 for s in TeamMemberStatus}
        role_counts = {}

        for member in self.members.values():
            status_counts[member.status.value] += 1
            role_counts[member.role] = role_counts.get(member.role, 0) + 1

        return {
            "team_name": self.team_name,
            "total_members": len(self.members),
            "status_counts": status_counts,
            "role_counts": role_counts,
        }


class HealthChecker:
    """
    Health monitoring for team members.

    Periodically checks if agents are responsive and
    updates their status accordingly.
    """

    def __init__(
        self,
        message_bus: MessageBus,
        team_manager: TeamManager,
        check_interval: float = 30.0,
        timeout: float = 10.0,
        max_missed_checks: int = 3,
        logger=None,
    ):
        """
        Initialize health checker.

        Args:
            message_bus: Message bus for health checks
            team_manager: Team manager for status updates
            check_interval: Seconds between health checks
            timeout: Seconds to wait for health response
            max_missed_checks: Number of missed checks before marking unresponsive
            logger: Optional logger
        """
        self.message_bus = message_bus
        self.team_manager = team_manager
        self.check_interval = check_interval
        self.timeout = timeout
        self.max_missed_checks = max_missed_checks
        self.logger = logger

        # Tracking
        self.missed_checks: Dict[str, int] = {}
        self.last_check_results: Dict[str, HealthCheckResult] = {}

        # Background task
        self._check_task: Optional["asyncio.Task"] = None
        self._running = False
        self._stop_event = threading.Event()

    async def start(self) -> None:
        """Start the health checker."""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()

        if self.logger:
            self.logger.info("Health checker started")

        # Run check loop
        import asyncio

        self._check_task = asyncio.create_task(self._check_loop())

    async def stop(self) -> None:
        """Stop the health checker."""
        if not self._running:
            return

        self._stop_event.set()
        self._running = False

        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass

        if self.logger:
            self.logger.info("Health checker stopped")

    async def _check_loop(self) -> None:
        """Main health check loop."""
        while not self._stop_event.is_set():
            await self._check_all_members()
            await asyncio.sleep(self.check_interval)

    async def _check_all_members(self) -> None:
        """Perform health checks on all members."""
        members = self.team_manager.get_all_members()

        for member in members:
            # Skip if this is the health checker itself
            if member.name == "health_checker":
                continue

            result = await self.check_agent_health(member.name)
            self.last_check_results[member.name] = result

            # Update member status based on health check
            if result.status == TeamMemberStatus.UNRESPONSIVE:
                self.team_manager.update_member_status(
                    member.name,
                    TeamMemberStatus.UNRESPONSIVE
                )
            elif result.status == TeamMemberStatus.ONLINE:
                self.team_manager.update_member_status(
                    member.name,
                    TeamMemberStatus.ONLINE
                )
                # Reset missed checks
                if member.name in self.missed_checks:
                    del self.missed_checks[member.name]

    async def check_agent_health(self, agent_name: str) -> HealthCheckResult:
        """
        Check if a specific agent is responsive.

        Args:
            agent_name: Name of agent to check

        Returns:
            HealthCheckResult
        """
        start_time = time.time()

        # Send health check
        self.message_bus.send(
            sender="health_checker",
            to=agent_name,
            content="ping",
            msg_type=MessageType.HEALTH_CHECK,
        )

        # Wait for response
        import asyncio

        try:
            await asyncio.wait_for(
                self._wait_for_health_response(agent_name),
                timeout=self.timeout,
            )

            response_time = (time.time() - start_time) * 1000

            # Reset missed checks on successful response
            if agent_name in self.missed_checks:
                del self.missed_checks[agent_name]

            return HealthCheckResult(
                agent_name=agent_name,
                status=TeamMemberStatus.ONLINE,
                response_time_ms=response_time,
                last_seen=time.time(),
            )

        except asyncio.TimeoutError:
            # Count missed check
            self.missed_checks[agent_name] = (
                self.missed_checks.get(agent_name, 0) + 1
            )

            # Check if agent is now unresponsive
            member = self.team_manager.get_member(agent_name)
            if member:
                last_seen = member.last_seen

                if self.missed_checks[agent_name] >= self.max_missed_checks:
                    return HealthCheckResult(
                        agent_name=agent_name,
                        status=TeamMemberStatus.UNRESPONSIVE,
                        response_time_ms=self.timeout * 1000,
                        last_seen=last_seen,
                        error=f"No response after {self.missed_checks[agent_name]} checks",
                    )
                else:
                    return HealthCheckResult(
                        agent_name=agent_name,
                        status=member.status,
                        response_time_ms=self.timeout * 1000,
                        last_seen=last_seen,
                        error=f"Timeout on check {self.missed_checks[agent_name]}/{self.max_missed_checks}",
                    )

            return HealthCheckResult(
                agent_name=agent_name,
                status=TeamMemberStatus.OFFLINE,
                response_time_ms=self.timeout * 1000,
                last_seen=0,
                error="Unknown agent",
            )

    async def _wait_for_health_response(self, agent_name: str) -> None:
        """
        Wait for health response from agent.

        Args:
            agent_name: Agent to wait for
        """
        import asyncio

        while True:
            await asyncio.sleep(0.1)
            inbox = self.message_bus.read_inbox("health_checker")

            for msg in inbox:
                if (
                    msg.type == MessageType.HEALTH_RESPONSE
                    and msg.from_agent == agent_name
                ):
                    return

    def get_health_report(self) -> Dict:
        """
        Get current health report.

        Returns:
            Dictionary with health status of all members
        """
        report = {
            "timestamp": time.time(),
            "members": {},
            "summary": {
                "online": 0,
                "offline": 0,
                "unresponsive": 0,
            },
        }

        for name, result in self.last_check_results.items():
            report["members"][name] = {
                "status": result.status.value,
                "response_time_ms": result.response_time_ms,
                "error": result.error,
            }
            report["summary"][result.status.value] += 1

        return report


def discover_teams(work_dir: Path) -> List[Dict]:
    """
    Discover all teams in the work directory.

    Args:
        work_dir: Directory to search for teams

    Returns:
        List of team information dictionaries
    """
    teams = []

    for team_dir in work_dir.glob(".team_*"):
        if team_dir.is_dir():
            team_name = team_dir.stem.replace(".team_", "")
            config_path = team_dir / "team_config.json"

            if config_path.exists():
                try:
                    config = json.loads(config_path.read_text(encoding="utf-8"))
                    teams.append({
                        "name": team_name,
                        "path": str(team_dir),
                        "config": config,
                    })
                except (json.JSONDecodeError, IOError):
                    pass

    return teams
