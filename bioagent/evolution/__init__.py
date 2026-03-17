"""
BioAgent Evolution System - Phase 10

Provides code evolution capabilities using MAP-Elites quality-diversity optimization,
hybrid evaluation (functional + LLM), and checkpoint/resume capabilities.

This system enables automatic improvement and optimization of tools and agent configurations.
"""

from bioagent.evolution.models import (
    EvolutionRun,
    EvolvedCode,
    GridCell,
    FitnessScore,
    EvolutionStatus,
    MutationType,
)
from bioagent.evolution.engine import EvolutionEngine
from bioagent.evolution.grid import MAPElitesGrid
from bioagent.evolution.evaluator import HybridEvaluator
from bioagent.evolution.strategies import (
    MutationStrategy,
    AnalyzerMutatorStrategy,
    CodeRewriterStrategy,
    ParameterTunerStrategy,
)
from bioagent.evolution.checkpoint import CheckpointManager
from bioagent.evolution.tools import (
    start_evolution,
    evolve_tool,
    get_evolution_status,
    pause_evolution,
    resume_evolution,
    get_evolved_tool,
    list_evolution_runs,
)

__all__ = [
    # Models
    "EvolutionRun",
    "EvolvedCode",
    "GridCell",
    "FitnessScore",
    "EvolutionStatus",
    "MutationType",
    # Core components
    "EvolutionEngine",
    "MAPElitesGrid",
    "HybridEvaluator",
    # Strategies
    "MutationStrategy",
    "AnalyzerMutatorStrategy",
    "CodeRewriterStrategy",
    "ParameterTunerStrategy",
    # Checkpoint
    "CheckpointManager",
    # Tools
    "start_evolution",
    "evolve_tool",
    "get_evolution_status",
    "pause_evolution",
    "resume_evolution",
    "get_evolved_tool",
    "list_evolution_runs",
]
