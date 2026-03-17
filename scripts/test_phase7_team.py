"""
Test script for Phase 7 Advanced Team Protocols.

Tests the following:
1. MessageBus - JSONL-based message passing
2. TeamProtocol - Request-response patterns
3. AutonomousAgent - Idle polling and auto-task claiming
4. KanbanBoard - Task visualization
5. TeamManager - Team state persistence
6. HealthChecker - Health monitoring
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bioagent.config import BioAgentConfig
from bioagent.team.protocol import (
    MessageBus,
    TeamProtocol,
    MessageType,
    Message,
    make_identity_block,
)
from bioagent.team.autonomous import (
    AutonomousAgent,
    AutonomousConfig,
    AgentStatus,
    AutonomousTeam,
)
from bioagent.team.kanban import KanbanBoard, SprintKanban
from bioagent.team.discovery import (
    TeamManager,
    HealthChecker,
    TeamMemberStatus,
    discover_teams,
)


async def test_message_bus():
    """Test MessageBus functionality."""
    print("\n=== Test: Message Bus ===")

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        inbox_dir = Path(tmpdir) / "inbox"
        bus = MessageBus(inbox_dir)

        # Send messages
        msg_id1 = bus.send(
            sender="agent1",
            to="agent2",
            content="Hello agent2!",
            msg_type=MessageType.MESSAGE,
        )
        print(f"✓ Sent message with ID: {msg_id1}")

        msg_id2 = bus.send(
            sender="agent1",
            to="agent2",
            content="Ping",
            msg_type=MessageType.PING,
        )
        print(f"✓ Sent ping with ID: {msg_id2}")

        # Read inbox
        messages = bus.read_inbox("agent2")
        print(f"✓ Received {len(messages)} messages")

        # Verify messages
        if len(messages) == 2:
            print("✓ MessageBus test PASSED")
            return True
        else:
            print(f"✗ MessageBus test FAILED: Expected 2 messages, got {len(messages)}")
            return False


async def test_team_protocol():
    """Test TeamProtocol request-response."""
    print("\n=== Test: Team Protocol ===")

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        inbox_dir = Path(tmpdir) / "inbox"
        bus = MessageBus(inbox_dir)

        protocol1 = TeamProtocol(bus, "agent1", None)
        protocol2 = TeamProtocol(bus, "agent2", None)

        # Test shutdown protocol
        print("Testing shutdown protocol...")
        protocol1.request_shutdown("agent2")
        messages = protocol2.message_bus.read_inbox("agent2")

        # Check for shutdown request
        shutdown_req = None
        for msg in messages:
            if msg.type == MessageType.SHUTDOWN_REQUEST:
                shutdown_req = msg
                break

        if shutdown_req:
            print(f"✓ Shutdown request received")

            # Handle the request
            await protocol2.handle_protocol_message(shutdown_req)

            # Check response
            responses = bus.read_inbox("agent1")
            if responses:
                print("✓ TeamProtocol test PASSED")
                return True

        print("✗ TeamProtocol test FAILED")
        return False


async def test_autonomous_agent():
    """Test AutonomousAgent basic functionality."""
    print("\n=== Test: Autonomous Agent ===")

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir)

        # Create message bus
        inbox_dir = work_dir / "inbox"
        bus = MessageBus(inbox_dir)

        # Create minimal config
        from bioagent.config import BioAgentConfig

        config = BioAgentConfig()
        config.enable_context_compression = False
        config.enable_task_tracking = False
        config.enable_background_tasks = False

        # Create a mock agent
        class MockAgent:
            def __init__(self):
                self.session_id = "test_agent"
                self.logger = None
                self.config = config

        mock_agent = MockAgent()

        # Create autonomous agent
        auto_config = AutonomousConfig(
            poll_interval=0.1,  # Fast for testing
            idle_timeout=1.0,
            max_idle_cycles=2,
        )

        autonomous = AutonomousAgent(
            agent=mock_agent,
            name="test_autonomous",
            role="tester",
            team_name="test_team",
            message_bus=bus,
            config=auto_config,
        )

        # Check status
        status = autonomous.get_status()
        print(f"✓ Agent status: {status['status']}")

        # Reset idle
        autonomous.reset_idle()
        print("✓ Idle cycles reset")

        if status["status"] == "initializing" and status["idle_cycles"] == 0:
            print("✓ AutonomousAgent test PASSED")
            return True
        else:
            print("✗ AutonomousAgent test FAILED")
            return False


async def test_kanban_board():
    """Test KanbanBoard visualization."""
    print("\n=== Test: Kanban Board ===")

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tasks_dir = Path(tmpdir) / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create mock task manager
        from bioagent.tasks.manager import TaskManager

        task_manager = TaskManager(tasks_dir, None)

        # Create some test tasks
        from bioagent.tasks.todo import TodoWrite
        from bioagent.observability import Logger

        logger = Logger("test", None)
        todo = TodoWrite(task_manager, logger)

        result1 = todo.create(
            "Task 1",
            "First test task",
            "Working on task 1",
            "high",
            persist=True,
        )
        task1_id = result1.get("id", "")

        result2 = todo.create(
            "Task 2",
            "Second test task",
            "Working on task 2",
            "medium",
            persist=True,
        )
        task2_id = result2.get("id", "")

        result3 = todo.create(
            "Task 3",
            "Third test task",
            "Working on task 3",
            "low",
            persist=True,
        )
        task3_id = result3.get("id", "")

        # Update statuses (note: owner can't be set directly via update_task)
        task_manager.update_task(task1_id, status="in_progress")
        task_manager.update_task(task2_id, status="completed")
        task_manager.update_task(task3_id, status="pending")

        # Create Kanban board
        kanban = KanbanBoard(task_manager)

        # Get summary
        summary = kanban.get_summary()
        print(f"✓ Status summary: {summary}")

        # Get priority summary
        priority_summary = kanban.get_priority_summary()
        print(f"✓ Priority summary: {priority_summary}")

        # Display board
        board = kanban.display()
        print(f"✓ Kanban board generated ({len(board)} chars)")

        if summary["pending"] == 1 and summary["in_progress"] == 1 and summary["completed"] == 1:
            print("✓ KanbanBoard test PASSED")
            return True
        else:
            print("✗ KanbanBoard test FAILED")
            return False


async def test_team_manager():
    """Test TeamManager persistence."""
    print("\n=== Test: Team Manager ===")

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        team_dir = Path(tmpdir)
        manager = TeamManager(team_dir, None)

        # Register members
        manager.register_member(
            "agent1", "researcher", ["analysis", "search"]
        )
        print("✓ Registered agent1")

        manager.register_member(
            "agent2", "analyzer", ["visualization", "processing"]
        )
        print("✓ Registered agent2")

        # Get team summary
        summary = manager.get_team_summary()
        print(f"✓ Team summary: {summary['total_members']} members")

        # Find member for task
        member = manager.find_member_for_task("analysis")
        print(f"✓ Found member for 'analysis': {member.name if member else None}")

        # Get members by role
        researchers = manager.get_members_by_role("researcher")
        print(f"✓ Found {len(researchers)} researchers")

        if (
            summary["total_members"] == 2
            and member
            and member.name == "agent1"
            and len(researchers) == 1
        ):
            print("✓ TeamManager test PASSED")
            return True
        else:
            print("✗ TeamManager test FAILED")
            return False


async def test_health_checker():
    """Test HealthChecker functionality."""
    print("\n=== Test: Health Checker ===")

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir)

        # Setup
        inbox_dir = work_dir / "inbox"
        bus = MessageBus(inbox_dir)

        team_manager = TeamManager(work_dir, None)
        team_manager.register_member("agent1", "tester")

        # Create health checker
        health_checker = HealthChecker(
            bus,
            team_manager,
            check_interval=0.5,
            timeout=1.0,
            max_missed_checks=2,
        )

        # Register a mock responding agent
        async def responder():
            while True:
                await asyncio.sleep(0.2)
                messages = bus.read_inbox("agent1")
                for msg in messages:
                    if msg.type == MessageType.HEALTH_CHECK:
                        bus.send(
                            sender="agent1",
                            to=msg.from_agent,
                            content="pong",
                            msg_type=MessageType.HEALTH_RESPONSE,
                            reply_to=msg.message_id,
                        )

        # Start responder
        asyncio.create_task(responder())

        # Start health checker
        await health_checker.start()
        print("✓ Health checker started")

        # Wait for one check cycle
        await asyncio.sleep(1.5)

        # Get health report
        report = health_checker.get_health_report()
        print(f"✓ Health report: {report['summary']}")

        # Stop health checker
        await health_checker.stop()
        print("✓ Health checker stopped")

        if report["summary"]["online"] > 0:
            print("✓ HealthChecker test PASSED")
            return True
        else:
            print("✗ HealthChecker test FAILED")
            return False


async def test_identity_block():
    """Test identity block generation."""
    print("\n=== Test: Identity Block ===")

    identity = make_identity_block(
        "researcher_1",
        "gene_analysis",
        "bio_team",
        additional_context="Current focus: TP53 pathway analysis",
    )

    print(f"✓ Generated identity block:")
    print(identity[:100] + "...")

    if "<identity>" in identity and "researcher_1" in identity:
        print("✓ Identity Block test PASSED")
        return True
    else:
        print("✗ Identity Block test FAILED")
        return False


async def run_tests(test_names: list = None):
    """Run all or selected tests."""
    tests = {
        "message_bus": test_message_bus,
        "team_protocol": test_team_protocol,
        "autonomous": test_autonomous_agent,
        "kanban": test_kanban_board,
        "team_manager": test_team_manager,
        "health_checker": test_health_checker,
        "identity_block": test_identity_block,
    }

    if test_names:
        tests_to_run = {name: tests[name] for name in test_names if name in tests}
    else:
        tests_to_run = tests

    print("=" * 60)
    print("Phase 7 Advanced Team Protocols Tests")
    print("=" * 60)

    results = []
    for name, test_func in tests_to_run.items():
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ Test '{name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{name:20} {status}")

    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\n{passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test Phase 7 Advanced Team Protocols"
    )
    parser.add_argument(
        "--test",
        nargs="+",
        choices=[
            "message_bus",
            "team_protocol",
            "autonomous",
            "kanban",
            "team_manager",
            "health_checker",
            "identity_block",
            "all",
        ],
        help="Specific tests to run (default: all)",
    )

    args = parser.parse_args()

    if args.test and "all" in args.test:
        args.test = None

    success = asyncio.run(run_tests(args.test))
    sys.exit(0 if success else 1)
