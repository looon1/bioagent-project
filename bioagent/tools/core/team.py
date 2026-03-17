"""
Team protocol tools for inter-agent communication.

Provides tools for:
- Team member discovery
- Health checks
- Task claiming
- Message passing between agents
"""

from typing import Dict, Any, Optional, TYPE_CHECKING

from bioagent.tools.base import tool

if TYPE_CHECKING:
    from bioagent.agent import Agent


@tool(domain="team")
async def team_ping(agent_name: str, context) -> str:
    """
    Send a ping to a team member to check if they are responsive.

    Use this to verify a teammate is online before assigning tasks.

    Args:
        agent_name: Name of the agent to ping
        context: Tool context containing agent instance

    Returns:
        Ping status message

    Example:
        >>> await team_ping("researcher_1", context)
        'Ping sent to researcher_1'
    """
    agent: "Agent" = context.get("agent")
    if not agent or not agent.context_manager or not hasattr(agent, "team_protocol"):
        return {"error": "Team protocol not available for this agent"}

    try:
        from bioagent.team.protocol import MessageType

        if hasattr(agent, "message_bus"):
            # Send ping
            agent.message_bus.send(
                sender=agent.session_id,
                to=agent_name,
                content="ping",
                msg_type=MessageType.PING,
            )
            return {"status": f"Ping sent to {agent_name}"}
        else:
            return {"error": "Message bus not available"}
    except Exception as e:
        return {"error": str(e)}


@tool(domain="team")
async def team_send_message(
    to_agent: str,
    message: str,
    context,
) -> Dict[str, str]:
    """
    Send a direct message to a team member.

    Use this for peer-to-peer communication within the team.

    Args:
        to_agent: Name of the agent to send message to
        message: Message content to send
        context: Tool context containing agent instance

    Returns:
        Message status

    Example:
        >>> await team_send_message("researcher_1", "I found interesting results")
        {'status': 'Message sent to researcher_1'}
    """
    agent: "Agent" = context.get("agent")
    if not agent or not hasattr(agent, "message_bus"):
        return {"error": "Message bus not available"}

    try:
        from bioagent.team.protocol import MessageType

        agent.message_bus.send(
            sender=agent.session_id,
            to=to_agent,
            content=message,
            msg_type=MessageType.MESSAGE,
        )
        return {"status": f"Message sent to {to_agent}"}
    except Exception as e:
        return {"error": str(e)}


@tool(domain="team")
async def team_check_inbox(context) -> Dict[str, Any]:
    """
    Check for incoming messages in the team inbox.

    Use this periodically to receive messages from other team members.

    Args:
        context: Tool context containing agent instance

    Returns:
        Dictionary with inbox information

    Example:
        >>> await team_check_inbox(context)
        {'count': 3, 'messages': [...]}
    """
    agent: "Agent" = context.get("agent")
    if not agent or not hasattr(agent, "message_bus"):
        return {"error": "Message bus not available"}

    try:
        from bioagent.team.protocol import Message

        messages = agent.message_bus.read_inbox(agent.session_id)
        return {
            "count": len(messages),
            "messages": [
                {
                    "from": msg.from_agent,
                    "content": msg.content[:100],  # Truncate for brevity
                    "type": msg.type.value,
                    "timestamp": msg.timestamp,
                }
                for msg in messages
            ],
        }
    except Exception as e:
        return {"error": str(e)}


@tool(domain="team")
async def team_claim_task(task_id: str, context) -> Dict[str, str]:
    """
    Claim a task from the team Kanban board.

    Use this when you want to take ownership of a task.

    Args:
        task_id: ID of the task to claim
        context: Tool context containing agent instance

    Returns:
        Claim status

    Example:
        >>> await team_claim_task("abc123", context)
        {'status': 'Claimed task abc123'}
    """
    agent: "Agent" = context.get("agent")
    if not agent or not agent.task_manager:
        return {"error": "Task manager not available"}

    try:
        result = agent.task_manager.update(
            task_id, status="in_progress", owner=agent.session_id
        )
        if result:
            return {"status": f"Claimed task {task_id}"}
        else:
            return {"error": f"Task {task_id} not found"}
    except Exception as e:
        return {"error": str(e)}


@tool(domain="team")
async def team_list_members(context) -> Dict[str, Any]:
    """
    List all registered team members.

    Use this to see who is on the team and their status.

    Args:
        context: Tool context containing agent instance

    Returns:
        Dictionary with team member information

    Example:
        >>> await team_list_members(context)
        {'members': [...], 'total': 5}
    """
    agent: "Agent" = context.get("agent")
    if not agent or not hasattr(agent, "team_manager"):
        return {"error": "Team manager not available"}

    try:
        from bioagent.team.discovery import TeamMemberStatus

        members = agent.team_manager.get_all_members()
        return {
            "total": len(members),
            "members": [
                {
                    "name": m.name,
                    "role": m.role,
                    "status": m.status.value,
                    "capabilities": m.capabilities,
                }
                for m in members
            ],
        }
    except Exception as e:
        return {"error": str(e)}


@tool(domain="team")
async def team_show_kanban(context, owner: Optional[str] = None) -> str:
    """
    Display the team Kanban board showing all tasks.

    Use this to get a visual overview of task status.

    Args:
        context: Tool context containing agent instance
        owner: Optional filter by specific team member

    Returns:
        Formatted Kanban board display

    Example:
        >>> await team_show_kanban(context)
        '===== KANBAN BOARD =====...'
    """
    agent: "Agent" = context.get("agent")
    if not agent or not hasattr(agent, "kanban_board"):
        return {"error": "Kanban board not available"}

    try:
        board = agent.kanban_board.display(owner=owner)
        return {"board": board}
    except Exception as e:
        return {"error": str(e)}


@tool(domain="team")
async def team_show_summary(context) -> Dict[str, Any]:
    """
    Show a summary of team task status.

    Use this to get quick statistics on team progress.

    Args:
        context: Tool context containing agent instance

    Returns:
        Dictionary with task summary statistics

    Example:
        >>> await team_show_summary(context)
        {'by_status': {...}, 'by_priority': {...}}
    """
    agent: "Agent" = context.get("agent")
    if not agent or not hasattr(agent, "kanban_board"):
        return {"error": "Kanban board not available"}

    try:
        status_summary = agent.kanban_board.get_summary()
        priority_summary = agent.kanban_board.get_priority_summary()

        return {
            "by_status": status_summary,
            "by_priority": priority_summary,
            "total_tasks": sum(status_summary.values()),
        }
    except Exception as e:
        return {"error": str(e)}


@tool(domain="team")
async def team_handoff(
    to_agent: str,
    context: str,
    context,
) -> Dict[str, str]:
    """
    Hand off a task to another team member.

    Use this when you cannot complete a task and need to pass it to someone else.

    Args:
        to_agent: Name of the agent to hand off to
        context: Context/instructions for the handoff
        context: Tool context containing agent instance

    Returns:
        Handoff status

    Example:
        >>> await team_handoff("specialist_1", "Need help with analysis")
        {'status': 'Handed off to specialist_1'}
    """
    agent: "Agent" = context.get("agent")
    if not agent or not hasattr(agent, "message_bus"):
        return {"error": "Message bus not available"}

    try:
        from bioagent.team.protocol import MessageType

        agent.message_bus.send(
            sender=agent.session_id,
            to=to_agent,
            content=context,
            msg_type=MessageType.HANDOFF_REQUEST,
        )
        return {"status": f"Handed off to {to_agent}"}
    except Exception as e:
        return {"error": str(e)}


@tool(domain="team")
async def team_register_as_member(
    role: str,
    capabilities: Optional[str] = None,
    context,
) -> Dict[str, str]:
    """
    Register yourself as a team member with a specific role.

    Use this when joining a team or to update your role/capabilities.

    Args:
        role: Your role (e.g., "researcher", "analyzer", "specialist")
        capabilities: Optional comma-separated list of capabilities
        context: Tool context containing agent instance

    Returns:
        Registration status

    Example:
        >>> await team_register_as_member("researcher", "gene_analysis, literature_search")
        {'status': 'Registered as researcher'}
    """
    agent: "Agent" = context.get("agent")
    if not agent or not hasattr(agent, "team_manager"):
        return {"error": "Team manager not available"}

    try:
        caps = [c.strip() for c in capabilities.split(",")] if capabilities else []

        agent.team_manager.register_member(
            name=agent.session_id,
            role=role,
            capabilities=caps,
        )
        return {"status": f"Registered as {role}"}
    except Exception as e:
        return {"error": str(e)}
