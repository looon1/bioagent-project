#!/usr/bin/env python3
"""
Test script for Phase 8: Worktree Isolation.

Tests worktree management, task binding, and event logging.
"""

import asyncio
import json
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from bioagent.config import BioAgentConfig
from bioagent.agent import Agent
from bioagent.worktree.manager import WorktreeManager, EventBus
from bioagent.observability import Logger


async def test_worktree_isolation():
    """Test worktree isolation functionality."""
    print("=" * 60)
    print("Phase 8: Worktree Isolation Test")
    print("=" * 60)

    # Initialize
    config = BioAgentConfig.from_env()
    logger = Logger("test_worktree")

    # Create test directories
    test_dir = Path.cwd() / "test_worktrees"
    test_tasks_dir = test_dir / ".tasks"
    test_worktrees_dir = test_dir / ".worktrees"
    test_tasks_dir.mkdir(parents=True, exist_ok=True)
    test_worktrees_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nTest directories:")
    print(f"  Tasks: {test_tasks_dir}")
    print(f"  Worktrees: {test_worktrees_dir}")

    # Initialize WorktreeManager
    worktree_mgr = WorktreeManager(
        repo_root=test_dir,
        tasks_dir=test_tasks_dir,
        worktrees_dir=test_worktrees_dir,
        logger=logger
    )

    print(f"\nWorktreeManager initialized:")
    print(f"  Git available: {worktree_mgr.git_available}")
    print(f"  Worktrees dir: {test_worktrees_dir}")

    # Test 1: Create worktree without task
    print("\n" + "-" * 60)
    print("Test 1: Create worktree without task binding")
    print("-" * 60)
    try:
        wt1 = worktree_mgr.create("test-worktree-1")
        print(f"Created worktree: {wt1['name']}")
        print(f"  Path: {wt1['path']}")
        print(f"  Branch: {wt1['branch']}")
        print(f"  Status: {wt1['status']}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 2: Create task and bind worktree
    print("\n" + "-" * 60)
    print("Test 2: Create task and bind worktree")
    print("-" * 60)

    # Create a task file manually
    task_id = "test-task-1"
    task_data = {
        "id": task_id,
        "subject": "Test task with worktree binding",
        "description": "This is a test task",
        "status": "pending",
        "worktree": "",
        "created_at": "2026-03-18T00:00:00Z",
        "updated_at": "2026-03-18T00:00:00Z",
    }
    task_file = test_tasks_dir / f"{task_id}.json"
    with open(task_file, "w") as f:
        json.dump(task_data, f, indent=2)

    print(f"Created test task: {task_id}")

    # Create worktree with task binding
    try:
        wt2 = worktree_mgr.create("test-worktree-2", task_id=task_id)
        print(f"Created worktree: {wt2['name']}")
        print(f"  Bound to task: {wt2['task_id']}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 3: List worktrees
    print("\n" + "-" * 60)
    print("Test 3: List all worktrees")
    print("-" * 60)
    worktrees = worktree_mgr.list_all()
    for wt in worktrees:
        task_info = f" (task: {wt['task_id']})" if wt.get('task_id') else ""
        print(f"  [{wt['status']}] {wt['name']}{task_info}")

    # Test 4: Get worktree status
    print("\n" + "-" * 60)
    print("Test 4: Get worktree status")
    print("-" * 60)
    try:
        status = worktree_mgr.status("test-worktree-1")
        print(f"Status of test-worktree-1:")
        print(f"  {status}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 5: List events
    print("\n" + "-" * 60)
    print("Test 5: List worktree events")
    print("-" * 60)
    events_json = worktree_mgr.list_events(limit=10)
    events = json.loads(events_json)
    for event in events:
        print(f"  [{event['event']}] ts={event['ts']}")

    # Test 6: Get summary
    print("\n" + "-" * 60)
    print("Test 6: Get worktree summary")
    print("-" * 60)
    summary = worktree_mgr.get_summary()
    print(f"  Total: {summary['total']}")
    print(f"  Active: {summary['active']}")
    print(f"  Removed: {summary['removed']}")
    print(f"  Kept: {summary['kept']}")
    print(f"  With task: {summary['with_task']}")

    # Test 7: Keep a worktree
    print("\n" + "-" * 60)
    print("Test 7: Mark worktree as kept")
    print("-" * 60)
    try:
        wt_kept = worktree_mgr.keep("test-worktree-1")
        print(f"Marked worktree as kept: {wt_kept['name']}")
        print(f"  New status: {wt_kept['status']}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 8: Remove worktree with task completion
    print("\n" + "-" * 60)
    print("Test 8: Remove worktree and complete task")
    print("-" * 60)
    try:
        result = worktree_mgr.remove("test-worktree-2", complete_task=True)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")

    # Verify task was completed
    with open(task_file, "r") as f:
        task_after = json.load(f)
    print(f"Task status after removal: {task_after['status']}")
    print(f"Task worktree after removal: {task_after.get('worktree', 'N/A')}")

    # Test 9: List worktrees again
    print("\n" + "-" * 60)
    print("Test 9: List worktrees after operations")
    print("-" * 60)
    worktrees = worktree_mgr.list_all()
    for wt in worktrees:
        task_info = f" (task: {wt['task_id']})" if wt.get('task_id') else ""
        print(f"  [{wt['status']}] {wt['name']}{task_info}")

    # Test 10: Test agent integration
    print("\n" + "-" * 60)
    print("Test 10: Test agent with worktree tools")
    print("-" * 60)
    try:
        agent = Agent(config=config)
        worktree_summary = agent.get_worktree_summary()
        print(f"Agent worktree summary:")
        print(f"  Enabled: {worktree_summary.get('enabled')}")
        print(f"  Worktrees dir: {worktree_summary.get('worktrees_dir')}")
        print(f"  Git available: {worktree_summary.get('git_available')}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60)
    print("Phase 8 Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_worktree_isolation())
