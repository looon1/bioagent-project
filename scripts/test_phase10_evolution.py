#!/usr/bin/env python
"""
Test script for BioAgent Phase 10: Code Evolution System.

Tests the evolution system components:
- Models (EvolutionRun, EvolvedCode, FitnessScore)
- MAP-Elites Grid
- Hybrid Evaluator
- Mutation Strategies
- Checkpoint System
- Evolution Engine
- Tool Integration
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from bioagent.config import BioAgentConfig
from bioagent.agent import Agent
from bioagent.evolution.models import (
    EvolutionRun,
    EvolvedCode,
    FitnessScore,
    GridCell,
    EvolutionStatus,
    MutationType,
    compute_behavior_vector,
    compute_behavior_index,
)
from bioagent.evolution.grid import MAPElitesGrid
from bioagent.evolution.evaluator import HybridEvaluator, create_default_test_cases
from bioagent.evolution.strategies import (
    AnalyzerMutatorStrategy,
    CodeRewriterStrategy,
    ParameterTunerStrategy,
)
from bioagent.evolution.checkpoint import CheckpointManager
from bioagent.evolution.engine import EvolutionEngine
from bioagent.llm import get_llm_provider
from bioagent.observability import Logger


class TestResults:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def record(self, test_name, passed, error=None):
        """Record test result."""
        if passed:
            self.passed += 1
            print(f"  ✓ {test_name}")
        else:
            self.failed += 1
            self.errors.append((test_name, error))
            print(f"  ✗ {test_name}: {error}")

    def summary(self):
        """Print summary."""
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Test Results: {self.passed}/{total} passed")
        print(f"{'='*60}")
        if self.errors:
            print("\nFailed tests:")
            for test_name, error in self.errors:
                print(f"  - {test_name}: {error}")
        return self.failed == 0


def test_models(results):
    """Test evolution data models."""
    print("\n[1/7] Testing Evolution Models")

    # Test FitnessScore
    fitness = FitnessScore(functional=0.8, llm_quality=0.7, diversity_bonus=0.1)
    results.record(
        "FitnessScore calculation",
        0.6*0.8 + 0.35*0.7 + 0.05*0.1 == fitness.combined
    )
    results.record(
        "FitnessScore serialization",
        "functional" in fitness.to_dict()
    )

    # Test EvolvedCode
    code = "def test(): return 42"
    evolved = EvolvedCode(
        id="test_evolved_001",
        code=code,
        generation=1,
        behavior_desc="Test function",
        behavior_vector=(0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    )
    results.record("EvolvedCode ID generation", bool(evolved.id))
    results.record(
        "EvolvedCode serialization",
        "code" in evolved.to_dict()
    )

    # Test EvolutionRun
    run = EvolutionRun(
        id="test_run_001",
        target_tool_name="test_tool",
        base_code=code,
    )
    results.record("EvolutionRun ID generation", bool(run.id))
    results.record("EvolutionRun status", run.status == EvolutionStatus.INITIALIZING)

    # Test behavior vector computation
    behavior = compute_behavior_vector(code, "A function that calculates things")
    results.record("Behavior vector length", len(behavior) == 7)
    results.record("Behavior vector normalization", all(0 <= b <= 1 for b in behavior))

    # Test behavior index computation
    idx = compute_behavior_index(behavior, 10)
    results.record("Behavior index computation", all(0 <= i < 10 for i in idx))


def test_grid(results):
    """Test MAP-Elites grid."""
    print("\n[2/7] Testing MAP-Elites Grid")

    grid = MAPElitesGrid(resolution=5, dimensions=2)

    # Test empty grid
    results.record("Grid initialization", grid.is_empty())
    results.record("Grid coverage (empty)", grid.get_coverage() == 0.0)

    # Create test evolved codes
    evolved1 = EvolvedCode(
        id="test_evolved_grid_001",
        code="def test1(): return 1",
        generation=1,
        behavior_desc="Test 1",
        behavior_vector=(0.2, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0),
    )
    evolved1.fitness = FitnessScore(functional=0.5, llm_quality=0.5, diversity_bonus=0.0)

    evolved2 = EvolvedCode(
        id="test_evolved_grid_002",
        code="def test2(): return 2",
        generation=1,
        behavior_desc="Test 2",
        behavior_vector=(0.8, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0),
    )
    evolved2.fitness = FitnessScore(functional=0.9, llm_quality=0.8, diversity_bonus=0.0)

    # Test insertion
    results.record("Grid insertion (first)", grid.insert(evolved1))
    results.record("Grid coverage (one cell)", grid.get_coverage() > 0)
    results.record("Grid insertion (improvement)", grid.insert(evolved2))

    # Test selection
    parents = grid.select_parents(2)
    results.record("Parent selection", len(parents) > 0)

    # Test elites
    elites = grid.get_elites()
    results.record("Get elites", len(elites) >= 1)

    # Test best
    best = grid.get_best()
    results.record("Get best", best is not None)

    # Test statistics
    stats = grid.get_statistics()
    results.record("Grid statistics", "coverage" in stats)


def test_evaluator(results):
    """Test hybrid evaluator."""
    print("\n[3/7] Testing Hybrid Evaluator")

    # Create minimal test configuration
    config = BioAgentConfig()

    # Set test mode to skip API validation
    os.environ["BIOAGENT_TEST_MODE"] = "true"

    # Initialize components (may fail without API keys, but that's OK for testing)
    try:
        logger = Logger("test_evolution", config)
        llm = get_llm_provider(config)
        evaluator = HybridEvaluator(llm, logger)

        results.record("Evaluator initialization", True)

        # Test default test cases
        test_cases = create_default_test_cases("query_uniprot")
        results.record("Default test cases", len(test_cases) > 0)

        # Test cache
        results.record("Evaluator cache (empty)", evaluator.cache_size() == 0)

        evaluator.clear_cache()
        results.record("Cache clear", evaluator.cache_size() == 0)

    except Exception as e:
        # Allow failures related to missing API keys
        if "API key" in str(e):
            print(f"  ℹ Skipping evaluator tests (API key required): {e}")
        else:
            raise


def test_strategies(results):
    """Test mutation strategies."""
    print("\n[4/7] Testing Mutation Strategies")

    # Create minimal test configuration
    config = BioAgentConfig()
    os.environ["BIOAGENT_TEST_MODE"] = "true"

    try:
        logger = Logger("test_strategies", config)
        llm = get_llm_provider(config)

        # Test AnalyzerMutatorStrategy
        analyzer = AnalyzerMutatorStrategy(llm, logger)
        results.record(
            "Analyzer strategy initialization",
            analyzer.get_type() == MutationType.ANALYZER_MUTATOR
        )

        # Test CodeRewriterStrategy
        rewriter = CodeRewriterStrategy(llm, logger)
        results.record(
            "Rewriter strategy initialization",
            rewriter.get_type() == MutationType.CODE_REWRITER
        )

        # Test ParameterTunerStrategy
        tuner = ParameterTunerStrategy(llm, logger)
        results.record(
            "Tuner strategy initialization",
            tuner.get_type() == MutationType.PARAMETER_TUNER
        )

        # Test strategy factory
        from bioagent.evolution.strategies import create_strategy

        strategy = create_strategy("analyzer_mutator", llm, logger)
        results.record("Strategy factory", strategy is not None)

    except Exception as e:
        if "API key" in str(e):
            print(f"  ℹ Skipping strategy tests (API key required): {e}")
        else:
            raise


def test_checkpoint(results):
    """Test checkpoint manager."""
    print("\n[5/7] Testing Checkpoint System")

    # Use temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = Logger("test_checkpoint", BioAgentConfig())
        manager = CheckpointManager(tmpdir, logger)

        # Test initialization
        results.record("Checkpoint manager initialization", True)

        # Test save
        checkpoint_path = manager.save_checkpoint(
            "test_run",
            1,
            {"test": "grid"},
            {"test": "run"}
        )
        results.record("Checkpoint save", Path(checkpoint_path).exists())

        # Test load
        loaded = manager.load_checkpoint(checkpoint_path)
        results.record("Checkpoint load", loaded is not None)
        if loaded:
            results.record("Checkpoint data integrity", loaded["generation"] == 1)

        # Test list
        checkpoints = manager.list_checkpoints()
        results.record("List checkpoints", len(checkpoints) > 0)

        # Test delete
        deleted = manager.delete_checkpoint(checkpoint_path)
        results.record("Delete checkpoint", deleted)

        # Test storage info
        info = manager.get_storage_info()
        results.record("Storage info", "checkpoint_count" in info)


def test_engine(results):
    """Test evolution engine."""
    print("\n[6/7] Testing Evolution Engine")

    # Create minimal test configuration
    config = BioAgentConfig()
    os.environ["BIOAGENT_TEST_MODE"] = "true"

    try:
        logger = Logger("test_engine", config)
        llm = get_llm_provider(config)

        # Test engine initialization
        engine_config = {
            "max_generations": 5,
            "population_size": 10,
            "grid_resolution": 5,
            "mutation_rate": 0.3,
            "evolution_dir": tempfile.gettempdir(),
        }

        engine = EvolutionEngine(engine_config, llm, logger)
        results.record("Engine initialization", True)

        # Test statistics
        stats = engine.get_statistics()
        results.record("Engine statistics", "status" in stats)

        # Test stop condition
        results.record("Engine not running initially", not engine.is_running())

    except Exception as e:
        if "API key" in str(e):
            print(f"  ℹ Skipping engine tests (API key required): {e}")
        else:
            raise


async def test_integration(results):
    """Test agent integration with evolution."""
    print("\n[7/7] Testing Agent Integration")

    # Create test configuration with evolution enabled
    config = BioAgentConfig()
    config.enable_evolution = True
    os.environ["BIOAGENT_TEST_MODE"] = "true"

    try:
        # Create agent with evolution enabled
        agent = Agent(config=config)

        # Test evolution enabled
        results.record("Agent evolution initialization", agent.config.enable_evolution)

        # Test evolution summary
        summary = agent.get_evolution_summary()
        results.record("Evolution summary", "enabled" in summary)

        # Test that evolution tools are registered
        tools = agent.tool_registry.list_tool_names()
        evolution_tools = [t for t in tools if "evolution" in t.lower()]
        results.record(
            "Evolution tools registered",
            len(evolution_tools) > 0
        )

        # Test tool availability
        has_evolve_tool = any("evolve_tool" in t for t in tools)
        results.record("Evolve tool available", has_evolve_tool)

    except Exception as e:
        if "API key" in str(e):
            print(f"  ℹ Skipping integration tests (API key required): {e}")
        else:
            raise


def main():
    """Run all tests."""
    print("="*60)
    print("BioAgent Phase 10: Evolution System Test Suite")
    print("="*60)

    results = TestResults()

    # Run synchronous tests
    test_models(results)
    test_grid(results)
    test_evaluator(results)
    test_strategies(results)
    test_checkpoint(results)
    test_engine(results)

    # Run async tests
    asyncio.run(test_integration(results))

    # Print summary and exit
    success = results.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
