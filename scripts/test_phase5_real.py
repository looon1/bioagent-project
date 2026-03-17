"""
Real-world test for Phase 5: Background Tasks.

This demonstrates:
1. Starting a long-running background task
2. Agent continuing to work while task runs
3. Checking task status
4. Receiving completion notification
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def demo_background_tasks():
    """Demonstrate background task functionality."""
    from bioagent.agent import Agent
    from bioagent.config import BioAgentConfig

    print("\n" + "=" * 70)
    print("Phase 5: Background Tasks - Real-World Demonstration")
    print("=" * 70 + "\n")

    # Create agent with background tasks enabled
    config = BioAgentConfig.from_env()
    config.enable_background_tasks = True
    config.background_task_timeout = 60

    agent = Agent(config=config)

    print("✓ Agent initialized with background task support")
    print(f"  Available tools: {len(agent.tool_registry)}")
    print(f"  Background manager: {'enabled' if agent.bg_manager else 'disabled'}\n")

    # Register a test long-running tool
    from bioagent.tools.base import tool

    @tool(domain="analysis")
    async def long_running_analysis(task_name: str, steps: int = 5) -> dict:
        """
        Perform a long-running data analysis with progress updates.

        Simulates a real data analysis that might take time to complete.

        Args:
            task_name: Name of the analysis task
            steps: Number of processing steps to simulate

        Returns:
            Analysis results dictionary
        """
        print(f"\n[Background Task] Starting {task_name}...")
        print(f"[Background Task] Processing {steps} steps...")

        results = []
        for i in range(steps):
            # Simulate processing time
            await asyncio.sleep(1.0)
            progress = ((i + 1) / steps) * 100
            print(f"[Background Task] Step {i+1}/{steps} completed ({progress:.0f}%)")
            results.append(f"Step {i+1}: Processed batch {i*1000}-{(i+1)*1000}")

        print(f"[Background Task] {task_name} completed successfully!")
        return {
            "task_name": task_name,
            "steps_completed": len(results),
            "results": results,
            "status": "completed"
        }

    agent.tool_registry.register(long_running_analysis)
    print("✓ Registered long_running_analysis tool\n")

    # ===== Scenario 1: Start a background task =====
    print("-" * 70)
    print("Scenario 1: Starting a Long-Running Background Task")
    print("-" * 70)

    query1 = "Start a background analysis of patient data with 5 steps"
    print(f"\nUser: {query1}")
    print("\nAgent: I'll start the long-running analysis in the background...")

    # Start background task via tool call
    result = await agent.execute(query1)
    print(f"\nAgent: {result}\n")

    # Get task ID from response
    import re
    task_id_match = re.search(r"task_id['\"]?\s*:\s*['\"]?([a-f0-9]+)['\"]?", result, re.IGNORECASE)
    if task_id_match:
        task_id = task_id_match.group(1)
        print(f"✓ Background task started with ID: {task_id}")
    else:
        print("Note: Task ID not found in response (simulated scenario)")

    # Let's manually create a background task for demonstration
    print("\n[Manual] Creating background task directly for demonstration...")

    async def analysis_coro():
        return await long_running_analysis("Patient Data Analysis", 5)

    bg_task = agent.bg_manager.start(
        tool_name="long_running_analysis",
        tool_call_id="demo_call_001",
        args={"task_name": "Patient Data Analysis", "steps": 5},
        coro=analysis_coro(),
        source="explicit",
    )
    print(f"✓ Background task created: {bg_task.task_id}")
    print(f"  Tool: {bg_task.tool_name}")
    print(f"  Status: {bg_task.status.value}\n")

    # ===== Scenario 2: Agent continues working while task runs =====
    print("-" * 70)
    print("Scenario 2: Agent Continues Working While Task Runs")
    print("-" * 70 + "\n")

    query2 = "What can I do while waiting for the analysis to complete?"
    print(f"User: {query2}")
    print("\nAgent: While the background analysis is running, I can:")

    response2 = await agent.execute(query2)
    print(f"\n{response2}\n")

    # ===== Scenario 3: Check task status =====
    print("-" * 70)
    print("Scenario 3: Checking Background Task Status")
    print("-" * 70 + "\n")

    query3 = "Check the status of the background analysis task"
    print(f"User: {query3}")
    print("\nAgent: Let me check the status of your background task...")

    response3 = await agent.execute(query3)
    print(f"\nAgent: {response3}\n")

    # Wait for task to complete
    print("-" * 70)
    print("Waiting for background task to complete...")
    print("-" * 70 + "\n")

    # Wait and poll status
    for _ in range(3):
        await asyncio.sleep(2)
        task = agent.bg_manager.get_task(bg_task.task_id)
        if task:
            print(f"Current status: {task.status.value}")
            if task.status.value == "completed":
                break

    # ===== Scenario 4: Task completion notification =====
    print("\n" + "-" * 70)
    print("Scenario 4: Task Completion Notification")
    print("-" * 70 + "\n")

    print("Simulating next user query to receive completion notification...")

    # Drain and show any notifications
    notifications = agent.bg_manager.drain_notifications()
    if notifications:
        print(f"\n✓ Received {len(notifications)} completion notification(s):\n")
        for notif in notifications:
            print(f"  Task ID: {notif.task_id}")
            print(f"  Status: {notif.status.value}")
            if notif.output_lines:
                print(f"  Recent output:")
                for line in notif.output_lines[-5:]:
                    print(f"    {line}")
            if notif.result:
                print(f"  Result: {notif.result}")
    else:
        # Force check of completed task
        task = agent.bg_manager.get_task(bg_task.task_id)
        if task and task.status.value == "completed":
            print(f"\n✓ Task {bg_task.task_id} completed!")
            print(f"  Final status: {task.status.value}")
            print(f"  Output lines captured: {len(task.output_lines)}")
            print(f"  Result available: {task.result is not None}")

    # ===== Scenario 5: Multiple concurrent tasks =====
    print("\n" + "-" * 70)
    print("Scenario 5: Multiple Concurrent Background Tasks")
    print("-" * 70 + "\n")

    print("Starting 3 concurrent background tasks...")

    task_names = ["Genomic Analysis", "Protein Folding", "Pathway Mapping"]
    bg_tasks = []

    for task_name in task_names:
        async def multi_analysis():
            return await long_running_analysis(task_name, 3)

        bg_task = agent.bg_manager.start(
            tool_name="long_running_analysis",
            tool_call_id=f"multi_{len(bg_tasks)}",
            args={"task_name": task_name, "steps": 3},
            coro=multi_analysis(),
            source="explicit",
        )
        bg_tasks.append(bg_task)
        print(f"✓ Started: {task_name} (ID: {bg_task.task_id})")

    print("\nWaiting for all tasks to complete...")
    await asyncio.sleep(4)

    # Check status of all tasks
    print("\nTask statuses:")
    for task in bg_tasks:
        current = agent.bg_manager.get_task(task.task_id)
        status = current.status.value if current else "unknown"
        print(f"  {task.task_id} ({task.tool_name}): {status}")

    # Get summary
    summary = agent.bg_manager.get_summary()
    print(f"\nBackground Task Manager Summary:")
    print(f"  Total tasks: {summary['total']}")
    print(f"  Running: {summary['running']}")
    print(f"  Completed: {summary['completed']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Cancelled: {summary['cancelled']}")

    # ===== Scenario 6: Cancel a running task =====
    print("\n" + "-" * 70)
    print("Scenario 6: Cancel a Running Task")
    print("-" * 70 + "\n")

    # Start a long task and immediately cancel it
    print("Starting a long task to cancel...")

    async def cancel_test_analysis():
        return await long_running_analysis("Cancellation Test", 100)

    cancel_task = agent.bg_manager.start(
        tool_name="long_running_analysis",
        tool_call_id="cancel_test",
        args={"task_name": "Cancellation Test", "steps": 100},
        coro=cancel_test_analysis(),
        source="explicit",
    )
    print(f"✓ Started task: {cancel_task.task_id}")

    await asyncio.sleep(0.5)
    print(f"\nCancelling task {cancel_task.task_id}...")

    cancelled = agent.bg_manager.cancel(cancel_task.task_id)
    if cancelled:
        print("✓ Task cancelled successfully")
        task = agent.bg_manager.get_task(cancel_task.task_id)
        print(f"  Final status: {task.status.value}")
    else:
        print("✗ Failed to cancel task")

    print("\n" + "=" * 70)
    print("Phase 5: Background Tasks - Demonstration Complete!")
    print("=" * 70)
    print("\nKey capabilities demonstrated:")
    print("  ✓ Start long-running operations in background")
    print("  ✓ Agent continues working while tasks run")
    print("  ✓ Check task status at any time")
    print("  ✓ Receive notifications when tasks complete")
    print("  ✓ Run multiple concurrent tasks")
    print("  ✓ Cancel running tasks")
    print()


if __name__ == "__main__":
    asyncio.run(demo_background_tasks())
