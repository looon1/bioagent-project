"""
Tests for Phase 2: Tool Adapter and Multi-Agent System.

Tests cover:
- ToolAdapter functionality
- BiomniToolAdapter integration
- Domain enable/disable
- SequentialTeam execution
- Configuration loading with new options
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from bioagent.tools.adapter import ToolAdapter, BiomniToolAdapter
from bioagent.tools.registry import ToolRegistry
from bioagent.tools.base import tool
from bioagent.config import BioAgentConfig
from bioagent.agent import Agent
from bioagent.agents.team import SequentialTeam


def test_tool_adapter_basic():
    """Test basic ToolAdapter functionality."""
    registry = ToolRegistry()
    adapter = ToolAdapter(registry)

    # Test domain listing (should be empty initially)
    domains = adapter.list_available_domains()
    assert isinstance(domains, list), "list_available_domains should return a list"
    assert len(domains) == 0, "No domains should be available initially"

    # Test enable/disable (should work even without tools)
    count = adapter.enable_domain("genetics")
    assert count == 0, "enable_domain should return 0 for empty domain"

    count = adapter.disable_domain("genetics")
    assert count == 0, "disable_domain should return 0 for empty domain"

    print("✓ test_tool_adapter_basic passed")


def test_biomni_adapter_without_biomni():
    """Test BiomniToolAdapter when Biomni is not installed."""
    registry = ToolRegistry()
    adapter = BiomniToolAdapter(registry, biomni_path="/nonexistent/path")

    # Register should gracefully handle missing Biomni
    count = adapter.register_all()
    assert count == 0, "Should register 0 tools when Biomni is not found"

    print("✓ test_biomni_adapter_without_biomni passed")


def test_biomni_adapter_mock_registration():
    """Test BiomniToolAdapter with mock tool registration."""
    registry = ToolRegistry()

    # Create a mock tool to register
    @tool(domain="test_domain")
    async def mock_tool(param1: str) -> str:
        """Mock tool for testing.

        Args:
            param1: Test parameter

        Returns:
            Test result
        """
        return f"Mock result: {param1}"

    # Register the tool
    registry.register(mock_tool)

    # Create adapter
    adapter = ToolAdapter(registry)

    # Test domain listing
    domains = adapter.list_available_domains()
    assert "test_domain" in domains, "Test domain should be available"

    # Test enable/disable
    adapter.disable_domain("test_domain")
    enabled_tools = adapter.get_enabled_tools(domain="test_domain")
    assert len(enabled_tools) == 0, "All tools should be disabled"

    adapter.enable_domain("test_domain")
    enabled_tools = adapter.get_enabled_tools(domain="test_domain")
    assert len(enabled_tools) == 1, "Tool should be enabled"

    print("✓ test_biomni_adapter_mock_registration passed")


def test_config_new_options():
    """Test configuration with new Phase 2 options."""
    # Test default values
    config = BioAgentConfig()

    assert config.enable_biomni_tools == False, "Biomni should be disabled by default"
    assert config.biomni_path is None, "Biomni path should be None by default"
    assert config.biomni_domains is None, "Biomni domains should be None by default"
    assert config.enable_multi_agent == False, "Multi-agent should be disabled by default"
    assert config.agent_team_mode == "single", "Team mode should be 'single' by default"

    # Test environment variable loading
    os.environ["BIOAGENT_ENABLE_BIOMNI"] = "true"
    os.environ["BIOAGENT_BIOMNI_PATH"] = "/custom/biomni/path"
    os.environ["BIOAGENT_BIOMNI_DOMAINS"] = "genetics,genomics"
    os.environ["BIOAGENT_ENABLE_MULTI_AGENT"] = "yes"
    os.environ["BIOAGENT_AGENT_TEAM_MODE"] = "sequential"

    config = BioAgentConfig.from_env()

    assert config.enable_biomni_tools == True, "Biomni should be enabled from env"
    assert config.biomni_path == "/custom/biomni/path", "Biomni path should be loaded from env"
    assert config.biomni_domains == ["genetics", "genomics"], "Biomni domains should be loaded from env"
    assert config.enable_multi_agent == True, "Multi-agent should be enabled from env"
    assert config.agent_team_mode == "sequential", "Team mode should be loaded from env"

    # Clean up
    del os.environ["BIOAGENT_ENABLE_BIOMNI"]
    del os.environ["BIOAGENT_BIOMNI_PATH"]
    del os.environ["BIOAGENT_BIOMNI_DOMAINS"]
    del os.environ["BIOAGENT_ENABLE_MULTI_AGENT"]
    del os.environ["BIOAGENT_AGENT_TEAM_MODE"]

    print("✓ test_config_new_options passed")


def test_config_validation():
    """Test configuration validation."""
    config = BioAgentConfig()
    config.api_key = "test_key"  # Set mock API key for validation

    # Should auto-enable multi-agent when team mode is not single
    config.agent_team_mode = "sequential"
    config.validate()
    assert config.enable_multi_agent == True, "Multi-agent should be auto-enabled when team mode is specified"

    # Reset and test again
    config = BioAgentConfig()
    config.api_key = "test_key"
    config.agent_team_mode = "single"
    config.validate()
    assert config.enable_multi_agent == False, "Multi-agent should remain disabled for single mode"

    print("✓ test_config_validation passed")


async def test_sequential_team():
    """Test SequentialTeam execution."""
    # Create a mock agent that doesn't require LLM
    class MockAgent:
        def __init__(self, session_id, response_prefix):
            self.session_id = session_id
            self.response_prefix = response_prefix
            self.tool_registry = None

        async def execute(self, query, context=None):
            return f"{self.response_prefix}: {query}"

    # Create mock agents
    agent1 = MockAgent("agent1", "Step1")
    agent2 = MockAgent("agent2", "Step2")
    agent3 = MockAgent("agent3", "Step3")

    # Create sequential team
    team = SequentialTeam([agent1, agent2, agent3], connect_prompt="Next:")

    # Execute
    result = await team.execute("test query")

    # Verify each agent processed the query
    assert "Step1:" in result, "First agent should have processed"
    assert "Step2:" in result, "Second agent should have processed"
    assert "Step3:" in result, "Third agent should have processed"

    print("✓ test_sequential_team passed")


def test_sequential_team_get_agent():
    """Test SequentialTeam agent lookup."""
    class MockAgent:
        def __init__(self, session_id):
            self.session_id = session_id
            self.tool_registry = None

        async def execute(self, query, context=None):
            return f"Response from {session_id}"

    agents = [
        MockAgent("agent1"),
        MockAgent("agent2"),
        MockAgent("agent3")
    ]

    team = SequentialTeam(agents)

    # Test get_agent
    agent = team.get_agent("agent2")
    assert agent.session_id == "agent2", "Should retrieve agent2"

    # Test list_agents
    agent_ids = team.list_agents()
    assert set(agent_ids) == {"agent1", "agent2", "agent3"}, "Should list all agents"

    print("✓ test_sequential_team_get_agent passed")


async def test_tool_wrapper_metadata():
    """Test that tool wrapper preserves metadata."""
    registry = ToolRegistry()
    adapter = ToolAdapter(registry)

    @tool(domain="test_metadata")
    async def test_func(x: int) -> str:
        """Test function with metadata.

        Args:
            x: Test parameter

        Returns:
            Result string
        """
        return f"Result: {x}"

    registry.register(test_func)

    # Get tool info
    tool_info = registry.get_tool("test_func")
    assert tool_info is not None, "Tool should be registered"
    assert tool_info.domain == "test_metadata", "Domain should be preserved"
    assert tool_info.name == "test_func", "Name should be preserved"

    print("✓ test_tool_wrapper_metadata passed")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Running Phase 2 Tests")
    print("=" * 60)
    print()

    # Synchronous tests
    test_tool_adapter_basic()
    test_biomni_adapter_without_biomni()
    test_biomni_adapter_mock_registration()
    test_config_new_options()
    test_config_validation()
    test_tool_wrapper_metadata()

    # Async tests
    asyncio.run(test_sequential_team())
    test_sequential_team_get_agent()

    print()
    print("=" * 60)
    print("All Phase 2 tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
