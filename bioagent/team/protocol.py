"""
Team Protocol and Message Bus for inter-agent communication.

Implements JSONL-based message passing, request-response patterns,
shutdown protocol, and plan approval workflow.
"""

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from bioagent.config import BioAgentConfig


class MessageType(str, Enum):
    """Types of messages in the team protocol."""
    # General messages
    MESSAGE = "message"
    PING = "ping"
    PONG = "pong"

    # Protocol messages
    SHUTDOWN_REQUEST = "shutdown_request"
    SHUTDOWN_RESPONSE = "shutdown_response"
    PLAN_APPROVAL_REQUEST = "plan_approval_request"
    PLAN_APPROVAL_RESPONSE = "plan_approval_response"
    HANDOFF_REQUEST = "handoff_request"
    HANDOFF_RESPONSE = "handoff_response"

    # Task messages
    TASK_CLAIMED = "task_claimed"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Health messages
    HEALTH_CHECK = "health_check"
    HEALTH_RESPONSE = "health_response"


@dataclass
class Message:
    """A message in the team protocol."""
    type: MessageType
    from_agent: str
    to_agent: str
    content: str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    reply_to: Optional[str] = None  # For request-response correlation
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type.value if isinstance(self.type, MessageType) else self.type,
            "from": self.from_agent,
            "to": self.to_agent,
            "content": self.content,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "reply_to": self.reply_to,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary."""
        type_value = data.get("type", "message")
        try:
            msg_type = MessageType(type_value)
        except ValueError:
            msg_type = MessageType.MESSAGE

        return cls(
            type=msg_type,
            from_agent=data["from"],
            to_agent=data["to"],
            content=data["content"],
            message_id=data.get("message_id", str(uuid.uuid4())[:8]),
            timestamp=data.get("timestamp", time.time()),
            reply_to=data.get("reply_to"),
            extra=data.get("extra", {}),
        )


class MessageBus:
    """
    JSONL-based message bus for inter-agent communication.

    Uses file-based inboxes for persistent, asynchronous communication
    between agents. Each agent has its own inbox file.
    """

    def __init__(self, inbox_dir: Path):
        """
        Initialize message bus.

        Args:
            inbox_dir: Directory for inbox files
        """
        self.dir = inbox_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def send(
        self,
        sender: str,
        to: str,
        content: str,
        msg_type: MessageType = MessageType.MESSAGE,
        reply_to: Optional[str] = None,
        extra: Dict[str, Any] = None,
    ) -> str:
        """
        Send a message to an agent.

        Args:
            sender: Name of sending agent
            to: Name of receiving agent
            content: Message content
            msg_type: Type of message
            reply_to: Optional message ID this is replying to
            extra: Optional additional data

        Returns:
            Message ID of sent message
        """
        msg = Message(
            type=msg_type,
            from_agent=sender,
            to_agent=to,
            content=content,
            reply_to=reply_to,
            extra=extra or {},
        )

        inbox_path = self.dir / f"{to}.jsonl"

        with self._lock:
            with open(inbox_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(msg.to_dict(), ensure_ascii=False) + "\n")

        return msg.message_id

    def read_inbox(self, name: str, drain: bool = True) -> List[Message]:
        """
        Read messages from an agent's inbox.

        Args:
            name: Agent name to read inbox for
            drain: Whether to clear the inbox after reading

        Returns:
            List of messages
        """
        inbox_path = self.dir / f"{name}.jsonl"

        if not inbox_path.exists():
            return []

        with self._lock:
            content = inbox_path.read_text(encoding="utf-8")
            messages = []
            for line in content.strip().splitlines():
                if line:
                    try:
                        messages.append(Message.from_dict(json.loads(line)))
                    except (json.JSONDecodeError, KeyError):
                        continue

            if drain:
                inbox_path.write_text("")

            return messages

    def clear_inbox(self, name: str) -> None:
        """
        Clear an agent's inbox.

        Args:
            name: Agent name
        """
        inbox_path = self.dir / f"{name}.jsonl"
        if inbox_path.exists():
            with self._lock:
                inbox_path.write_text("")

    def list_inboxes(self) -> List[str]:
        """
        List all active inboxes.

        Returns:
            List of agent names with inboxes
        """
        inboxes = []
        for path in self.dir.glob("*.jsonl"):
            inboxes.append(path.stem)
        return inboxes


class TeamProtocol:
    """
    Team protocol framework with request-response, shutdown, and plan approval.

    Manages protocol state and message correlation.
    """

    def __init__(self, message_bus: MessageBus, agent_name: str, logger=None):
        """
        Initialize team protocol.

        Args:
            message_bus: Message bus instance
            agent_name: Name of this agent
            logger: Optional logger instance
        """
        self.message_bus = message_bus
        self.agent_name = agent_name
        self.logger = logger

        # Request tracking for correlation
        self._active_requests: Dict[str, Callable] = {}
        self._request_lock = threading.Lock()

        # Protocol state
        self.shutdown_requested = False
        self.shutdown_granted = False

        # Plan approval tracking
        self._pending_plans: Dict[str, dict] = {}

    def register_request_handler(
        self, request_id: str, callback: Callable[[Message], Any]
    ) -> None:
        """
        Register a callback for a specific request ID.

        Args:
            request_id: Request ID to watch for
            callback: Function to call when response arrives
        """
        with self._request_lock:
            self._active_requests[request_id] = callback

    def send_request(
        self,
        to: str,
        content: str,
        msg_type: MessageType = MessageType.MESSAGE,
        timeout: float = 30.0,
    ) -> Optional[Message]:
        """
        Send a request and wait for response.

        Args:
            to: Target agent
            content: Request content
            msg_type: Type of request message
            timeout: Seconds to wait for response

        Returns:
            Response message or None if timeout
        """
        request_id = self.message_bus.send(
            sender=self.agent_name,
            to=to,
            content=content,
            msg_type=msg_type,
        )

        # Wait for response
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = self._check_for_response(request_id)
            if response:
                return response
            time.sleep(0.1)

        return None

    def _check_for_response(self, request_id: str) -> Optional[Message]:
        """
        Check inbox for response to specific request.

        Args:
            request_id: Request ID to look for

        Returns:
            Response message or None
        """
        inbox = self.message_bus.read_inbox(self.agent_name, drain=False)

        for msg in inbox:
            if msg.reply_to == request_id:
                # Found response
                self.message_bus.clear_inbox(self.agent_name)

                # Call registered callback if any
                with self._request_lock:
                    callback = self._active_requests.pop(request_id, None)
                    if callback:
                        callback(msg)

                return msg

        return None

    async def handle_protocol_message(self, msg: Message) -> Optional[str]:
        """
        Handle protocol-specific messages.

        Args:
            msg: Incoming message

        Returns:
            Optional response message content
        """
        if msg.type == MessageType.SHUTDOWN_REQUEST:
            return await self._handle_shutdown_request(msg)

        elif msg.type == MessageType.SHUTDOWN_RESPONSE:
            with self._request_lock:
                self.shutdown_granted = True

        elif msg.type == MessageType.PLAN_APPROVAL_REQUEST:
            return await self._handle_plan_approval_request(msg)

        elif msg.type == MessageType.PLAN_APPROVAL_RESPONSE:
            with self._request_lock:
                plan_id = msg.extra.get("plan_id")
                if plan_id:
                    self._pending_plans[plan_id] = msg.extra

        elif msg.type == MessageType.HEALTH_CHECK:
            # Respond to health check
            self.message_bus.send(
                sender=self.agent_name,
                to=msg.from_agent,
                content="pong",
                msg_type=MessageType.HEALTH_RESPONSE,
                reply_to=msg.message_id,
            )
            return None

        return None

    async def _handle_shutdown_request(self, msg: Message) -> str:
        """
        Handle a shutdown request.

        Args:
            msg: Shutdown request message

        Returns:
            Response content
        """
        self.shutdown_requested = True

        if self.logger:
            self.logger.info(
                "Shutdown requested",
                from_agent=msg.from_agent,
                request_id=msg.message_id,
            )

        # Grant shutdown (in real implementation, might check conditions)
        self.message_bus.send(
            sender=self.agent_name,
            to=msg.from_agent,
            content="Shutdown granted",
            msg_type=MessageType.SHUTDOWN_RESPONSE,
            reply_to=msg.message_id,
        )

        return "Shutdown granted"

    async def _handle_plan_approval_request(self, msg: Message) -> str:
        """
        Handle a plan approval request.

        Args:
            msg: Plan approval request message

        Returns:
            Response content
        """
        plan_text = msg.content
        plan_id = msg.message_id

        if self.logger:
            self.logger.info(
                "Plan approval requested",
                from_agent=msg.from_agent,
                plan_id=plan_id,
                plan_preview=plan_text[:100],
            )

        # For now, auto-approve all plans
        # In production, this would trigger LLM review
        approved = True
        feedback = "" if approved else "Plan needs revision"

        self.message_bus.send(
            sender=self.agent_name,
            to=msg.from_agent,
            content=feedback,
            msg_type=MessageType.PLAN_APPROVAL_RESPONSE,
            reply_to=plan_id,
            extra={
                "plan_id": plan_id,
                "approved": approved,
            },
        )

        return f"Plan {'approved' if approved else 'rejected'}"

    def request_plan_approval(
        self, to: str, plan_text: str, timeout: float = 60.0
    ) -> Optional[dict]:
        """
        Request approval for a plan.

        Args:
            to: Agent to request approval from (e.g., team lead)
            plan_text: Plan to be approved
            timeout: Seconds to wait for approval

        Returns:
            Approval response dict with 'approved' and 'feedback' keys
        """
        response = self.send_request(
            to=to,
            content=plan_text,
            msg_type=MessageType.PLAN_APPROVAL_REQUEST,
            timeout=timeout,
        )

        if response:
            return {
                "approved": response.extra.get("approved", False),
                "feedback": response.content,
            }

        return None

    def request_shutdown(self, to: str, timeout: float = 30.0) -> bool:
        """
        Request shutdown of another agent.

        Args:
            to: Agent to shut down
            timeout: Seconds to wait for response

        Returns:
            True if shutdown was granted
        """
        response = self.send_request(
            to=to,
            content="Requesting shutdown",
            msg_type=MessageType.SHUTDOWN_REQUEST,
            timeout=timeout,
        )

        return response is not None


def make_identity_block(
    name: str, role: str, team_name: str, additional_context: str = ""
) -> str:
    """
    Create an identity block for re-injection after context compression.

    Args:
        name: Agent name
        role: Agent role
        team_name: Team name
        additional_context: Additional context to include

    Returns:
        Identity block as a string
    """
    identity = f"""<identity>
You are '{name}', role: {role}, team: {team_name}.
Continue your work from where you left off.
{additional_context}
</identity>"""
    return identity
