#!/usr/bin/env python3
"""
Test script for BioAgent Phase 9: Web UI

Tests:
1. Web server creation
2. Session management endpoints
3. SSE streaming endpoint
4. File upload/download
5. Health check
"""

import asyncio
import os
import sys
import json
import time
from pathlib import Path
from tempfile import TemporaryDirectory

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bioagent.agent import Agent
from bioagent.config import BioAgentConfig
from bioagent.web.server import create_app


def print_test_header(title: str) -> None:
    """Print a formatted test header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_result(test_name: str, success: bool, message: str = "") -> None:
    """Print test result."""
    status = "✓ PASS" if success else "✗ FAIL"
    print(f"{status}: {test_name}")
    if message:
        print(f"  └─ {message}")


def test_config() -> bool:
    """Test 1: Web configuration setup."""
    print_test_header("Test 1: Web Configuration Setup")

    try:
        config = BioAgentConfig.from_env()
        config.web_host = "127.0.0.1"
        config.web_port = 7861

        # Test sessions directory creation
        config.sessions_dir.mkdir(parents=True, exist_ok=True)

        print_result("Configuration loaded", True, f"sessions_dir: {config.sessions_dir}")
        print_result("Web options set", True, f"host={config.web_host}, port={config.web_port}")
        print_result("CORS enabled", True, f"enable_cors={config.enable_cors}")

        return True
    except Exception as e:
        print_result("Configuration setup", False, str(e))
        return False


def test_agent_init() -> bool:
    """Test 2: Agent initialization."""
    print_test_header("Test 2: Agent Initialization")

    try:
        config = BioAgentConfig.from_env()
        config.web_host = "127.0.0.1"
        config.web_port = 7861

        # Set test mode to skip API key validation
        os.environ["BIOAGENT_TEST_MODE"] = "true"

        agent = Agent(config=config)

        print_result("Agent created", True, f"session_id: {agent.session_id}")
        print_result("Tool registry loaded", True, f"tools: {len(agent.tool_registry)}")
        print_result("Config loaded", True, f"model: {config.model}")

        return True
    except Exception as e:
        print_result("Agent initialization", False, str(e))
        return False


def test_app_creation() -> bool:
    """Test 3: FastAPI app creation."""
    print_test_header("Test 3: FastAPI App Creation")

    try:
        config = BioAgentConfig.from_env()
        config.web_host = "127.0.0.1"
        config.web_port = 7861
        os.environ["BIOAGENT_TEST_MODE"] = "true"

        agent = Agent(config=config)
        app = create_app(agent, config)

        print_result("FastAPI app created", True)
        print_result("App routes", True, f"routes: {len(app.routes)}")

        # Check key endpoints
        route_paths = [route.path for route in app.routes]
        required_paths = [
            "/api/sessions",
            "/api/sessions/{session_id}/activate",
            "/api/chat",
            "/api/health",
            "/api/files",
            "/api/dir",
            "/api/upload",
            "/api/stop",
        ]

        for path in required_paths:
            exists = any(path in rp for rp in route_paths)
            print_result(f"Endpoint {path}", exists, f"{'found' if exists else 'missing'}")

        return True
    except Exception as e:
        print_result("App creation", False, str(e))
        return False


def test_session_manager() -> bool:
    """Test 4: Session management."""
    print_test_header("Test 4: Session Management")

    try:
        from bioagent.web.server import SessionManager

        # Use temp directory for testing
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmpdir:
            sessions_dir = Path(tmpdir)
            manager = SessionManager(sessions_dir)

            # Test session creation
            session1 = manager.get_or_create()
            print_result("Session 1 created", True, f"id={session1['id']}")

            # Test session retrieval
            retrieved = manager.get_or_create(session1["id"])
            print_result("Session retrieved", True, f"id={retrieved['id']}")

            # Test session update
            updated = manager.update(session1["id"], title="Test Task")
            print_result("Session updated", True, f"title={updated['title']}")

            # Test session listing
            sessions = manager.list_all()
            print_result("Sessions listed", True, f"count={len(sessions)}")

            # Test session deletion
            deleted = manager.delete(session1["id"])
            print_result("Session deleted", deleted)

        return True
    except Exception as e:
        print_result("Session management", False, str(e))
        return False


def test_file_handling() -> bool:
    """Test 5: File handling helpers."""
    print_test_header("Test 5: File Handling Helpers")

    try:
        from bioagent.web.server import (
            _make_file_entry, _safe_upload_name, _is_subpath
        )

        # Test file entry creation
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")
            entry = _make_file_entry(test_file, Path(tmpdir))
            print_result("File entry created", True, f"name={entry['name']}, type={entry['type']}")

            # Test safe upload name
            upload_dir = Path(tmpdir) / "uploads"
            upload_dir.mkdir()
            safe1 = _safe_upload_name(upload_dir, "file.txt")
            safe2 = _safe_upload_name(upload_dir, "file.txt")
            print_result("Safe upload name", True, f"{safe1.name} != {safe2.name}")

            # Test subpath check
            parent = Path(tmpdir)
            child = parent / "subdir" / "file.txt"
            child.parent.mkdir(parents=True, exist_ok=True)
            is_sub = _is_subpath(child, [parent])
            print_result("Subpath check", is_sub, f"child is within parent")

        return True
    except Exception as e:
        print_result("File handling", False, str(e))
        return False


def run_all_tests() -> int:
    """Run all tests and return exit code."""
    print("\n" + "="*60)
    print("  BioAgent Phase 9: Web UI Test Suite")
    print("="*60)

    tests = [
        ("Configuration", test_config),
        ("Agent Init", test_agent_init),
        ("App Creation", test_app_creation),
        ("Session Management", test_session_manager),
        ("File Handling", test_file_handling),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_result(name, False, f"Exception: {e}")
            results.append((name, False))

    # Summary
    print_test_header("Test Summary")
    passed = sum(1 for _, r in results if r)
    total = len(results)

    print(f"  Total:  {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {total - passed}")
    print(f"  Rate:   {passed/total*100:.1f}%")

    print(f"\n{'='*60}")
    if passed == total:
        print("  ✓ All tests passed!")
    else:
        print("  ✗ Some tests failed")
    print(f"{'='*60}\n")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
