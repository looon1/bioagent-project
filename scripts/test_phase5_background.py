"""
Comprehensive test script for Phase 5 Background Tasks implementation.

Tests:
1. BackgroundTaskManager initialization
2. Task creation and execution
3. Output capture
4. Task status tracking
5. Notification draining
6. Task cancellation
7. Task eviction
8. Agent integration
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bioagent.background.manager import (
    BackgroundTask,
    BackgroundTaskStatus,
    BackgroundTaskManager,
)
from bioagent.background.capture import (
    _bg_output_buffer,
    _bg_report,
)
from bioagent.observability import Logger


async def test_background_task_manager():
    """Test BackgroundTaskManager functionality."""
    print("=" * 70)
    print("Test 1: BackgroundTaskManager Initialization")
    print("=" * 70)

    logger = Logger("test_bg")
    bg_manager = BackgroundTaskManager(max_retained=5, logger=logger)

    # Verify initialization
    summary = bg_manager.get_summary()
    assert summary["total"] == 0
    assert summary["running"] == 0
    print("✓ BackgroundTaskManager initialized correctly")
    print(f"  Summary: {summary}")


async def test_task_creation():
    """Test creating and starting background tasks."""
    print("\n" + "=" * 70)
    print("Test 2: Task Creation and Execution")
    print("=" * 70)

    logger = Logger("test_bg")
    bg_manager = BackgroundTaskManager(max_retained=5, logger=logger)

    # Define a simple async task
    async def simple_task():
        await asyncio.sleep(0.1)
        return "Task completed successfully"

    # Start task
    task = bg_manager.start(
        tool_name="test_tool",
        tool_call_id="call_123",
        args={"param": "value"},
        coro=simple_task(),
        source="explicit",
    )

    # Verify task was created
    assert task.task_id is not None
    assert task.status == BackgroundTaskStatus.RUNNING
    assert task.tool_name == "test_tool"
    print(f"✓ Task {task.task_id} created and started")
    print(f"  Status: {task.status.value}")
    print(f"  Tool: {task.tool_name}")

    # Wait for task completion
    await asyncio.sleep(0.2)

    # Verify task completed
    task = bg_manager.get_task(task.task_id)
    assert task is not None
    assert task.status == BackgroundTaskStatus.COMPLETED
    assert task.result == "Task completed successfully"
    print(f"✓ Task {task.task_id} completed successfully")
    print(f"  Result: {task.result}")


async def test_output_capture():
    """Test output capture from background tasks."""
    print("\n" + "=" * 70)
    print("Test 3: Output Capture")
    print("=" * 70)

    logger = Logger("test_bg")
    bg_manager = BackgroundTaskManager(max_retained=5, logger=logger)

    # Define a task that prints output
    async def task_with_output():
        print("Starting task...")
        await asyncio.sleep(0.05)
        print("Processing...")
        await asyncio.sleep(0.05)
        print("Done!")
        return "Complete"

    # Start task
    task = bg_manager.start(
        tool_name="test_output",
        tool_call_id="call_456",
        args={},
        coro=task_with_output(),
        source="explicit",
    )

    # Wait for completion
    await asyncio.sleep(0.2)

    # Verify output was captured
    task = bg_manager.get_task(task.task_id)
    assert task is not None
    assert len(task.output_lines) > 0
    print(f"✓ Output captured correctly")
    print(f"  Output lines: {len(task.output_lines)}")
    for line in task.output_lines:
        print(f"    - {line}")


async def test_notification_draining():
    """Test notification draining for completed tasks."""
    print("\n" + "=" * 70)
    print("Test 4: Notification Draining")
    print("=" * 70)

    logger = Logger("test_bg")
    bg_manager = BackgroundTaskManager(max_retained=5, logger=logger)

    # Start multiple tasks
    tasks = []
    for i in range(3):
        async def task_fn(idx=i):
            await asyncio.sleep(0.05)
            return f"Task {idx} result"

        task = bg_manager.start(
            tool_name=f"test_notification_{i}",
            tool_call_id=f"call_{i}",
            args={},
            coro=task_fn(),
            source="explicit",
        )
        tasks.append(task)

    # Wait for all tasks to complete
    await asyncio.sleep(0.3)

    # Drain notifications
    notifications = bg_manager.drain_notifications()
    assert len(notifications) == 3
    print(f"✓ Drained {len(notifications)} notifications")

    for i, notif in enumerate(notifications):
        assert notif.status == BackgroundTaskStatus.COMPLETED
        print(f"  Notification {i+1}: Task {notif.task_id} - {notif.status.value}")

    # Verify notifications queue is empty
    notifications = bg_manager.drain_notifications()
    assert len(notifications) == 0
    print("✓ Notification queue cleared after draining")


async def test_task_cancellation():
    """Test task cancellation."""
    print("\n" + "=" * 70)
    print("Test 5: Task Cancellation")
    print("=" * 70)

    logger = Logger("test_bg")
    bg_manager = BackgroundTaskManager(max_retained=5, logger=logger)

    # Define a long-running task
    async def long_task():
        await asyncio.sleep(10)
        return "Should not reach here"

    # Start task
    task = bg_manager.start(
        tool_name="long_task",
        tool_call_id="call_long",
        args={},
        coro=long_task(),
        source="explicit",
    )

    # Cancel immediately
    cancelled = bg_manager.cancel(task.task_id)
    assert cancelled == True
    print(f"✓ Task {task.task_id} cancelled successfully")

    # Wait a bit and verify status
    await asyncio.sleep(0.1)
    task = bg_manager.get_task(task.task_id)
    assert task.status == BackgroundTaskStatus.CANCELLED
    print(f"  Status: {task.status.value}")


async def test_task_eviction():
    """Test old task eviction."""
    print("\n" + "=" * 70)
    print("Test 6: Task Eviction")
    print("=" * 70)

    logger = Logger("test_bg")
    bg_manager = BackgroundTaskManager(max_retained=3, logger=logger)

    # Create and complete multiple tasks
    for i in range(5):
        async def task_fn(idx=i):
            await asyncio.sleep(0.05)
            return f"Task {idx}"

        task = bg_manager.start(
            tool_name=f"test_eviction_{i}",
            tool_call_id=f"call_ev_{i}",
            args={},
            coro=task_fn(),
            source="explicit",
        )
        await asyncio.sleep(0.1)

    # Wait for all to complete
    await asyncio.sleep(0.2)

    # Check summary - only max_retained completed tasks should be kept
    summary = bg_manager.get_summary()
    total_tasks = bg_manager.get_all_tasks()
    completed_tasks = [t for t in total_tasks if t.status == BackgroundTaskStatus.COMPLETED]

    # Should have at most max_retained completed tasks
    assert len(completed_tasks) <= bg_manager.max_retained
    print(f"✓ Old tasks evicted correctly")
    print(f"  Total tasks: {summary['total']}")
    print(f"  Completed: {summary['completed']}")
    print(f"  Max retained: {bg_manager.max_retained}")


async def test_agent_integration():
    """Test agent integration with background tasks."""
    print("\n" + "=" * 70)
    print("Test 7: Agent Integration")
    print("=" * 70)

    from bioagent.agent import Agent
    from bioagent.config import BioAgentConfig

    # Create agent with background tasks enabled
    config = BioAgentConfig.from_env()
    config.enable_background_tasks = True

    agent = Agent(config=config)

    # Verify bg_manager is initialized
    assert agent.bg_manager is not None
    print("✓ BackgroundTaskManager initialized in Agent")

    # Verify background tools are registered
    tools = agent.get_enabled_tools(domain="background")
    bg_tool_names = [t.name for t in tools if "background" in t.name]
    assert len(bg_tool_names) > 0
    print(f"✓ Background tools registered: {bg_tool_names}")

    # Check background manager summary
    summary = agent.bg_manager.get_summary()
    print(f"  Summary: {summary}")


async def test_bg_report():
    """Test _bg_report helper function."""
    print("\n" + "=" * 70)
    print("Test 8: _bg_report Helper")
    print("=" * 70)

    from bioagent.background.capture import _bg_report, _bg_output_buffer

    # Set a buffer context
    buffer = []
    token = _bg_output_buffer.set(buffer)

    # Report messages
    _bg_report("Progress update 1")
    _bg_report("Progress update 2")

    # Verify messages were captured
    assert len(buffer) == 2
    assert buffer[0] == "Progress update 1"
    assert buffer[1] == "Progress update 2"
    print("✓ _bg_report captured messages correctly")
    print(f"  Messages: {buffer}")

    # Reset context
    _bg_output_buffer.reset(token)


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("Phase 5: Background Tasks - Comprehensive Tests")
    print("=" * 70 + "\n")

    tests = [
        test_background_task_manager,
        test_task_creation,
        test_output_capture,
        test_notification_draining,
        test_task_cancellation,
        test_task_eviction,
        test_agent_integration,
        test_bg_report,
    ]

    failed = []
    for test in tests:
        try:
            await test()
        except Exception as e:
            print(f"\n✗ Test failed: {test.__name__}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            failed.append(test.__name__)

    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    if failed:
        print(f"✗ {len(failed)} test(s) failed:")
        for name in failed:
            print(f"  - {name}")
    else:
        print(f"✓ All {len(tests)} tests passed!")

    print("\n" + "=" * 70)
    print("Phase 5: Background Tasks - Implementation Complete!")
    print("=" * 70)

    return len(failed) == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
