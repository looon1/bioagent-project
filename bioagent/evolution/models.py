"""
Data models for the evolution system.

Defines the core data structures used throughout the evolution process.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import json


class EvolutionStatus(Enum):
    """Status of an evolution run."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    RESUMING = "resuming"


class MutationType(Enum):
    """Type of mutation strategy."""
    ANALYZER_MUTATOR = "analyzer_mutator"
    CODE_REWRITER = "code_rewriter"
    PARAMETER_TUNER = "parameter_tuner"
    HYBRID = "hybrid"


@dataclass
class FitnessScore:
    """Composite fitness score combining functional and LLM evaluation."""
    functional: float = 0.0  # 0-1, from test case execution
    llm_quality: float = 0.0  # 0-1, from LLM code quality assessment
    diversity_bonus: float = 0.0  # 0-1, bonus for diverse solutions
    combined: float = 0.0  # Weighted combination

    def __post_init__(self):
        """Calculate combined score."""
        self.combined = (
            0.6 * self.functional +
            0.35 * self.llm_quality +
            0.05 * self.diversity_bonus
        )

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "functional": self.functional,
            "llm_quality": self.llm_quality,
            "diversity_bonus": self.diversity_bonus,
            "combined": self.combined,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "FitnessScore":
        """Create from dictionary."""
        return cls(
            functional=data.get("functional", 0.0),
            llm_quality=data.get("llm_quality", 0.0),
            diversity_bonus=data.get("diversity_bonus", 0.0),
        )


@dataclass
class EvolvedCode:
    """Represents a code variant with metadata."""
    id: str
    code: str
    generation: int
    parent_ids: List[str] = field(default_factory=list)
    mutation_type: MutationType = MutationType.HYBRID
    fitness: FitnessScore = field(default_factory=FitnessScore)
    behavior_desc: str = ""
    behavior_vector: Tuple[float, ...] = ()
    created_at: datetime = field(default_factory=datetime.utcnow)
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    llm_feedback: str = ""

    def __post_init__(self):
        """Generate ID if not provided."""
        if not self.id:
            code_hash = hashlib.md5(self.code.encode()).hexdigest()[:8]
            self.id = f"{self.mutation_type.value}_{code_hash}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "code": self.code,
            "generation": self.generation,
            "parent_ids": self.parent_ids,
            "mutation_type": self.mutation_type.value,
            "fitness": self.fitness.to_dict(),
            "behavior_desc": self.behavior_desc,
            "behavior_vector": self.behavior_vector,
            "created_at": self.created_at.isoformat(),
            "test_results": self.test_results,
            "llm_feedback": self.llm_feedback,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvolvedCode":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            code=data["code"],
            generation=data["generation"],
            parent_ids=data.get("parent_ids", []),
            mutation_type=MutationType(data.get("mutation_type", "hybrid")),
            fitness=FitnessScore.from_dict(data.get("fitness", {})),
            behavior_desc=data.get("behavior_desc", ""),
            behavior_vector=tuple(data.get("behavior_vector", ())),
            created_at=datetime.fromisoformat(data["created_at"]),
            test_results=data.get("test_results", []),
            llm_feedback=data.get("llm_feedback", ""),
        )


@dataclass
class GridCell:
    """Cell in the MAP-Elites grid."""
    behavior_idx: Tuple[int, ...]
    code: Optional[EvolvedCode] = None

    def is_occupied(self) -> bool:
        """Check if cell has an occupant."""
        return self.code is not None

    def fitness(self) -> float:
        """Get fitness of occupant."""
        return self.code.fitness.combined if self.code else 0.0


@dataclass
class EvolutionRun:
    """Tracks a complete evolution experiment."""
    id: str
    target_tool_name: str
    base_code: str
    status: EvolutionStatus = EvolutionStatus.INITIALIZING
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    current_generation: int = 0
    max_generations: int = 50
    population_size: int = 20
    grid_resolution: int = 10
    mutation_rate: float = 0.3
    best_fitness: float = 0.0
    best_code: Optional[EvolvedCode] = None
    config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Generate ID if not provided."""
        if not self.id:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            self.id = f"evolution_{self.target_tool_name}_{timestamp}"

    def duration(self) -> Optional[float]:
        """Get duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.status in [EvolutionStatus.RUNNING, EvolutionStatus.RESUMING]:
            return (datetime.utcnow() - self.start_time).total_seconds()
        return None

    def is_running(self) -> bool:
        """Check if run is active."""
        return self.status in [EvolutionStatus.RUNNING, EvolutionStatus.RESUMING]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "target_tool_name": self.target_tool_name,
            "base_code": self.base_code,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "current_generation": self.current_generation,
            "max_generations": self.max_generations,
            "population_size": self.population_size,
            "grid_resolution": self.grid_resolution,
            "mutation_rate": self.mutation_rate,
            "best_fitness": self.best_fitness,
            "best_code": self.best_code.to_dict() if self.best_code else None,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvolutionRun":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            target_tool_name=data["target_tool_name"],
            base_code=data["base_code"],
            status=EvolutionStatus(data.get("status", "initializing")),
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            current_generation=data.get("current_generation", 0),
            max_generations=data.get("max_generations", 50),
            population_size=data.get("population_size", 20),
            grid_resolution=data.get("grid_resolution", 10),
            mutation_rate=data.get("mutation_rate", 0.3),
            best_fitness=data.get("best_fitness", 0.0),
            best_code=EvolvedCode.from_dict(data["best_code"]) if data.get("best_code") else None,
            config=data.get("config", {}),
        )

    def save(self, path: str) -> None:
        """Save evolution run to file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "EvolutionRun":
        """Load evolution run from file."""
        with open(path, "r") as f:
            return cls.from_dict(json.load(f))


def compute_behavior_vector(code: str, desc: str) -> Tuple[float, ...]:
    """
    Compute behavior vector for MAP-Elites.

    Maps code to a behavior space based on:
    1. Code complexity (loc, cyclomatic complexity)
    2. Code characteristics (uses lists, dicts, imports certain modules)

    Args:
        code: Source code string
        desc: Description of the code's behavior

    Returns:
        Tuple of floats representing behavior vector
    """
    # Normalize to [0, 1] range
    lines = len(code.split("\n"))
    complexity = min(lines / 100, 1.0)  # Normalize by 100 lines

    # Check for specific patterns
    uses_list = "list" in code.lower()
    uses_dict = "dict" in code.lower()
    uses_async = "async" in code.lower()

    # Description-based features
    desc_lower = desc.lower()
    has_math = any(w in desc_lower for w in ["calculate", "compute", "math"])
    has_io = any(w in desc_lower for w in ["read", "write", "file", "output"])
    has_network = any(w in desc_lower for w in ["fetch", "request", "http", "api"])

    return (
        complexity,
        float(uses_list),
        float(uses_dict),
        float(uses_async),
        float(has_math),
        float(has_io),
        float(has_network),
    )


def compute_behavior_index(
    behavior_vector: Tuple[float, ...],
    resolution: int
) -> Tuple[int, ...]:
    """
    Convert behavior vector to grid index.

    Args:
        behavior_vector: Normalized behavior vector
        resolution: Grid resolution per dimension

    Returns:
        Tuple of grid indices
    """
    return tuple(
        min(int(b * resolution), resolution - 1)
        for b in behavior_vector
    )
