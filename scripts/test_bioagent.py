"""
Test script for BioAgent Phase 1 implementation.

This script demonstrates the basic functionality without requiring an API key.
"""

import asyncio
from bioagent.tools.registry import ToolRegistry
from bioagent.tools.base import tool as tool_decorator, get_tool_info, is_tool
from bioagent.tools.loader import ToolLoader
from bioagent.observability import Logger, Metrics, CostTracker
from bioagent.config import BioAgentConfig


def test_tool_decorator():
    """Test @tool_decorator decorator functionality."""
    print("\n=== Testing @tool_decorator decorator ===")

    @tool_decorator(domain="test")
    def sample_function(name: str, count: int = 1) -> str:
        """A sample function for testing."""
        return f"Hello {name}! Count: {count}"

    # Check if function is marked as tool
    assert is_tool(sample_function), "Function should be marked as tool"
    print("✓ Function is marked as tool")

    # Get tool info
    info = get_tool_info(sample_function)
    assert info is not None, "Should have tool info"
    print(f"✓ Tool name: {info.name}")
    print(f"✓ Tool description: {info.description}")
    print(f"✓ Tool domain: {info.domain}")

    # Check parameters
    assert "properties" in info.parameters, "Should have parameters"
    assert "name" in info.parameters["properties"], "Should have name parameter"
    assert "count" in info.parameters["properties"], "Should have count parameter"
    print("✓ Parameters parsed correctly")

    return sample_function


async def test_tool_registry():
    """Test ToolRegistry functionality."""
    print("\n=== Testing ToolRegistry ===")

    registry = ToolRegistry()
    print(f"✓ Empty registry has {len(registry)} tools")

    # Register a tool
    @tool_decorator
    async def test_tool_1(param: str) -> str:
        """First test tool."""
        return f"Test: {param}"

    registry.register(test_tool_1)
    print(f"✓ Registered 1 tool, registry now has {len(registry)} tools")

    # Register another tool
    @tool_decorator(domain="analysis")
    async def test_tool_2(value: int) -> int:
        """Second test tool."""
        return value * 2

    registry.register(test_tool_2)
    print(f"✓ Registered 2nd tool, registry now has {len(registry)} tools")

    # List tools
    all_tools = registry.list_tool_names()
    print(f"✓ Tool names: {all_tools}")

    # Get specific tool
    tool = registry.get_tool("test_tool_1")
    assert tool is not None, "Should find tool"
    print(f"✓ Found tool: {tool.name}")

    # Execute tool
    result = await registry.execute("test_tool_1", {"param": "Hello"})
    assert result == "Test: Hello", f"Unexpected result: {result}"
    print(f"✓ Tool execution result: {result}")

    # List by domain
    analysis_tools = registry.list_tool_names(domain="analysis")
    assert "test_tool_2" in analysis_tools, "Should find analysis domain tool"
    assert "test_tool_1" not in analysis_tools, "Should not find general domain tool"
    print(f"✓ Analysis domain tools: {analysis_tools}")

    # Test OpenAI format
    openai_tools = registry.to_openai_format()
    assert len(openai_tools) == 2, "Should have 2 tools"
    assert openai_tools[0]["name"] in ["test_tool_1", "test_tool_2"], "Tool name mismatch"
    print(f"✓ OpenAI format generated for {len(openai_tools)} tools")


async def test_tool_loader():
    """Test ToolLoader functionality."""
    print("\n=== Testing ToolLoader ===")

    registry = ToolRegistry()
    loader = ToolLoader(registry)

    # Create a temporary tool file
    import tempfile
    import os
    with tempfile.TemporaryDirectory() as tmpdir:
        tool_file = os.path.join(tmpdir, "test_tool.py")

        with open(tool_file, 'w') as f:
            f.write('''
from bioagent.tools.base import tool as tool_decorator

@tool_decorator(domain="loaded")
async def loaded_tool(message: str) -> str:
    """A tool loaded dynamically."""
    return f"Loaded: {message}"
''')

        # Load from directory
        loader.load_from_directory(tmpdir)
        loaded_tools = registry.list_tool_names(domain="loaded")
        assert "loaded_tool" in loaded_tools, "Should load tool from directory"
        print(f"✓ Loaded tools from directory: {loaded_tools}")

        # Execute loaded tool
        result = await registry.execute("loaded_tool", {"message": "Success!"})
        assert result == "Loaded: Success!", f"Unexpected result: {result}"
        print(f"✓ Loaded tool executed: {result}")


def test_observability():
    """Test observability components."""
    print("\n=== Testing Observability ===")

    # Logger
    logger = Logger("test")
    print("✓ Logger initialized")

    logger.info("Test message", extra={"test_key": "test_value"})
    print("✓ Info log written")

    logger.error("Test error", extra={"error_code": 500})
    print("✓ Error log written")

    # Metrics
    metrics = Metrics()
    print("✓ Metrics initialized")

    metrics.increment("test.counter")
    assert metrics.get_counter("test.counter") == 1, "Counter should be 1"
    print(f"✓ Counter incremented: {metrics.get_counter('test.counter')}")

    metrics.timing("test.timing", 123.45)
    timings = metrics.get_timings("test.timing")
    assert len(timings) == 1, "Should have 1 timing"
    assert timings[0] == 123.45, f"Unexpected timing: {timings[0]}"
    print(f"✓ Timing recorded: {timings}")

    metrics.record_llm_call("test-model", 100, 500)
    summary = metrics.get_summary()
    assert summary["counters"]["llm.calls"] == 1, "Should have 1 LLM call"
    print(f"✓ LLM call recorded in metrics")

    # Cost tracker
    cost_tracker = CostTracker()
    print("✓ Cost tracker initialized")

    cost = cost_tracker.record("claude-3-5-haiku-20241022", 1000, 500)
    assert cost > 0, "Cost should be positive"
    print(f"✓ Cost recorded: ${cost:.6f}")

    total = cost_tracker.get_total_cost()
    assert total == cost, "Total cost should match recorded cost"
    print(f"✓ Total cost: ${total:.6f}")

    summary = cost_tracker.get_token_summary()
    assert "claude-3-5-haiku-20241022" in summary, "Should have model in summary"
    print(f"✓ Token summary: {summary}")


def test_config():
    """Test configuration management."""
    print("\n=== Testing Configuration ===")

    config = BioAgentConfig()
    print(f"✓ Default config created")
    print(f"  Model: {config.model}")
    print(f"  Max tokens: {config.max_tokens}")
    print(f"  Data path: {config.data_path}")
    print(f"  Logs path: {config.logs_path}")

    # Test env config
    import os
    original_model = os.getenv("BIOAGENT_MODEL")
    os.environ["BIOAGENT_MODEL"] = "test-model"

    env_config = BioAgentConfig.from_env()
    assert env_config.model == "test-model", "Should load model from env"
    print(f"✓ Model from env: {env_config.model}")

    # Restore original
    if original_model is None:
        os.environ.pop("BIOAGENT_MODEL", None)
    else:
        os.environ["BIOAGENT_MODEL"] = original_model


async def test_core_tools():
    """Test core tools (without API calls)."""
    print("\n=== Testing Core Tools ===")

    # Test write_file
    from bioagent.tools.core.files import write_file
    result = await write_file("/tmp/test_bioagent.txt", "Test content")
    assert result["success"], f"Write failed: {result}"
    print(f"✓ File written: {result}")

    # Test read_file
    from bioagent.tools.core.files import read_file
    result = await read_file("/tmp/test_bioagent.txt")
    assert result["success"], f"Read failed: {result}"
    assert "Test content" in result["content"], f"Unexpected content: {result['content']}"
    print(f"✓ File read: {result['content']}")

    # Test run_python_code
    from bioagent.tools.core.analysis import run_python_code
    result = await run_python_code("x = 5 * 3; print(x)")
    assert result["success"], f"Code execution failed: {result}"
    assert "15" in result["output"], f"Unexpected output: {result['output']}"
    print(f"✓ Code executed: {result['output']}")


async def main():
    """Run all tests."""
    print("="*60)
    print("BioAgent Phase 1 Test Suite")
    print("="*60)

    try:
        test_tool_decorator()
        await test_tool_registry()
        await test_tool_loader()
        test_observability()
        test_config()
        await test_core_tools()

        print("\n" + "="*60)
        print("✓ All tests passed!")
        print("="*60)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
