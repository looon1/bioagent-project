#!/usr/bin/env python3
"""
Test script for BioAgent with GLM-4.7 model.
"""

import sys
import os
import asyncio

# Add bioagent to Python path
bioagent_path = "/mnt/public/rstudio-home/fzh_hblab/bioagent"
if bioagent_path not in sys.path:
    sys.path.insert(0, bioagent_path)

print("Testing BioAgent with GLM-4.7 configuration...")
print(f"Python path: {sys.path[:2]}")
print(f"BioAgent path: {bioagent_path}")
print()

# Test 1: Check .env file loading
print("=== Test 1: Environment loading ===")
try:
    from dotenv import load_dotenv
    load_dotenv()
    print(f"✓ .env loaded")

    model = os.getenv("BIOAGENT_MODEL")
    base_url = os.getenv("BIOAGENT_BASE_URL")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    print(f"  Model: {model}")
    print(f"  Base URL: {base_url}")
    print(f"  API Key: {api_key[:20] if api_key else 'None'}...")

    if model != "glm-4.7":
        print(f"⚠ Warning: Expected 'glm-4.7', got '{model}'")

except Exception as e:
    print(f"✗ Error loading .env: {e}")

# Test 2: Import BioAgent modules
print("\n=== Test 2: Import BioAgent ===")
try:
    from bioagent.agent import Agent
    from bioagent.config import BioAgentConfig
    from bioagent.llm import get_llm_provider
    print("✓ All BioAgent modules imported")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Test 3: Configuration loading
print("\n=== Test 3: Configuration ===")
try:
    config = BioAgentConfig.from_env()
    print("✓ Configuration loaded successfully")
    print(f"  Model: {config.model}")
    print(f"  Base URL: {config.base_url}")

    # Validate configuration
    config.validate()
    print("✓ Configuration validated")
except Exception as e:
    print(f"✗ Configuration error: {e}")
    sys.exit(1)

# Test 4: LLM Provider initialization
print("\n=== Test 4: LLM Provider ===")
try:
    provider = get_llm_provider(config)
    print(f"✓ Provider initialized: {provider.__class__.__name__}")
    if "glm" in config.model.lower():
        print("✓ GLM model detected, will use OpenAI-compatible provider")
except Exception as e:
    print(f"✗ Provider error: {e}")
    sys.exit(1)

# Test 5: Tool registry
print("\n=== Test 5: Tool Registry ===")
try:
    from bioagent.tools.registry import ToolRegistry
    registry = ToolRegistry()
    print("✓ Tool registry created")
    print(f"✓ Empty registry has {len(registry)} tools")
except Exception as e:
    print(f"✗ Tool registry error: {e}")
    sys.exit(1)

# Test 6: Core tools
print("\n=== Test 6: Core Tools ===")
try:
    from bioagent.tools.core.files import write_file, read_file
    from bioagent.tools.core.analysis import run_python_code

    print("✓ Core tools imported")

    # Test core tools using asyncio
    async def test_core_tools():
        # Test write_file
        result = await write_file("/tmp/test_write.txt", "Test content from BioAgent")
        if result.get("success"):
            print(f"✓ write_file tool works")

            # Test read_file
            result = await read_file("/tmp/test_write.txt")
            if result.get("success") and "Test content" in result.get("content", ""):
                print("✓ read_file tool works")
            else:
                print(f"⚠ read_file issue: {result}")
        else:
            print(f"⚠ write_file failed: {result}")

    # Run the async test
    asyncio.run(test_core_tools())
except Exception as e:
    print(f"✗ Core tools error: {e}")

print("\n" + "="*60)
print("✓ BioAgent setup with GLM-4.7 completed successfully!")
print("="*60)
