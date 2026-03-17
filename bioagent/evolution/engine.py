"""
Evolution engine coordinator.

Manages the overall evolution process including grid, evaluator,
strategies, and checkpointing.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from bioagent.evolution.grid import MAPElitesGrid
from bioagent.evolution.evaluator import HybridEvaluator, create_default_test_cases
from bioagent.evolution.strategies import (
    create_strategy,
    MutationStrategy,
)
from bioagent.evolution.checkpoint import CheckpointManager
from bioagent.evolution.models import (
    EvolutionRun,
    EvolutionStatus,
    EvolvedCode,
    MutationType,
    compute_behavior_vector,
)
from bioagent.observability import Logger


class EvolutionEngine:
    """
    Main coordinator for code evolution runs.

    Manages the evolution loop, grid, evaluation, and checkpointing.
    """

    def __init__(
        self,
        config: Dict,
        llm_provider,
        logger: Logger,
    ):
        """
        Initialize the evolution engine.

        Args:
            config: Evolution configuration dictionary
            llm_provider: LLM provider for code generation
            logger: Logger for recording events
        """
        self.config = config
        self.llm = llm_provider
        self.logger = logger

        # Evolution state
        self.run: Optional[EvolutionRun] = None
        self.grid: Optional[MAPElitesGrid] = None
        self.evaluator: Optional[HybridEvaluator] = None
        self.checkpoint_manager: Optional[CheckpointManager] = None

        # Strategies
        self.strategies: List[MutationStrategy] = []
        self._init_strategies()

        # Runtime state
        self._running = False
        self._paused = False
        self._stop_requested = False

    def _init_strategies(self) -> None:
        """Initialize mutation strategies."""
        strategy_types = [
            "analyzer_mutator",
            "code_rewriter",
            "parameter_tuner",
        ]

        for strategy_type in strategy_types:
            try:
                strategy = create_strategy(strategy_type, self.llm, self.logger)
                self.strategies.append(strategy)
                self.logger.debug(f"Initialized strategy: {strategy_type}")
            except Exception as e:
                self.logger.warning(f"Failed to initialize strategy {strategy_type}: {e}")

    async def start_evolution(
        self,
        tool_name: str,
        base_code: str,
        test_cases: Optional[List[Dict]] = None,
        resume_from: Optional[str] = None
    ) -> EvolutionRun:
        """
        Start a new evolution run or resume an existing one.

        Args:
            tool_name: Name of the tool to evolve
            base_code: Starting code (or ignored if resuming)
            test_cases: Test cases for evaluation
            resume_from: Checkpoint path to resume from

        Returns:
            Evolution run object
        """
        # Initialize components
        evolution_dir = Path(self.config.get("evolution_dir", ".evolution"))
        self.checkpoint_manager = CheckpointManager(str(evolution_dir), self.logger)
        self.evaluator = HybridEvaluator(self.llm, self.logger)

        # Resume or create new run
        if resume_from:
            self.logger.info(f"Resuming evolution from checkpoint: {resume_from}")
            checkpoint_data = self.checkpoint_manager.load_checkpoint(resume_from)

            if checkpoint_data:
                self.run = EvolutionRun.from_dict(checkpoint_data["run"])
                self.grid = MAPElitesGrid(
                    resolution=self.run.grid_resolution,
                    dimensions=7
                )
                self.grid.load_from_dict(checkpoint_data["grid"])
            else:
                raise ValueError(f"Failed to load checkpoint: {resume_from}")
        else:
            # Create new run
            self.run = EvolutionRun(
                target_tool_name=tool_name,
                base_code=base_code,
                max_generations=self.config.get("max_generations", 50),
                population_size=self.config.get("population_size", 20),
                grid_resolution=self.config.get("grid_resolution", 10),
                mutation_rate=self.config.get("mutation_rate", 0.3),
            )

            # Initialize grid
            self.grid = MAPElitesGrid(
                resolution=self.run.grid_resolution,
                dimensions=7
            )

            # Evaluate and insert base code
            base_evolved = await self._evaluate_base_code(
                base_code,
                tool_name,
                test_cases or create_default_test_cases(tool_name)
            )
            self.grid.insert(base_evolved)
            self.run.best_code = base_evolved
            self.run.best_fitness = base_evolved.fitness.combined

        # Set run status
        self.run.status = EvolutionStatus.RUNNING if not resume_from else EvolutionStatus.RESUMING
        self._running = True
        self._paused = False
        self._stop_requested = False

        self.logger.info(
            "Evolution started",
            run_id=self.run.id,
            tool_name=tool_name,
            max_generations=self.run.max_generations,
        )

        return self.run

    async def _evaluate_base_code(
        self,
        code: str,
        tool_name: str,
        test_cases: List[Dict]
    ) -> EvolvedCode:
        """Evaluate the base code."""
        behavior_desc = f"Tool: {tool_name} - Base implementation"
        behavior_vector = compute_behavior_vector(code, behavior_desc)

        base_evolved = EvolvedCode(
            id="base",
            code=code,
            generation=0,
            behavior_desc=behavior_desc,
            behavior_vector=behavior_vector,
        )

        # Evaluate
        await self.evaluator.evaluate(base_evolved, test_cases)

        return base_evolved

    async def evolve_generation(self) -> Dict:
        """
        Execute one generation of evolution.

        Returns:
            Dictionary with generation statistics
        """
        if not self.run or not self.grid:
            raise RuntimeError("Evolution not started")

        self.run.current_generation += 1
        generation = self.run.current_generation

        self.logger.info(f"Starting generation {generation}", run_id=self.run.id)

        # Select parents
        parents = self.grid.select_parents(self.run.population_size)
        if not parents:
            self.logger.warning("No parents selected for generation")
            return {"generation": generation, "new_variants": 0}

        # Generate offspring
        new_variants = []
        for parent in parents:
            # Select random strategy
            strategy = self.strategies[len(new_variants) % len(self.strategies)]

            # Mutate
            try:
                offspring = await strategy.mutate(
                    parent,
                    generation,
                    self.run.mutation_rate
                )
                new_variants.append(offspring)
            except Exception as e:
                self.logger.warning(f"Mutation failed: {e}")

        # Evaluate offspring
        test_cases = self.run.config.get("test_cases")
        existing_behaviors = [c.behavior_desc for c in self.grid.get_elites()]

        for variant in new_variants:
            try:
                await self.evaluator.evaluate(variant, test_cases or [], existing_behaviors)

                # Insert into grid
                inserted = self.grid.insert(variant)

                if inserted and variant.fitness.combined > self.run.best_fitness:
                    self.run.best_fitness = variant.fitness.combined
                    self.run.best_code = variant
                    self.logger.info(
                        "New best solution found",
                        generation=generation,
                        fitness=variant.fitness.combined,
                    )

            except Exception as e:
                self.logger.warning(f"Evaluation failed for variant {variant.id}: {e}")

        # Save checkpoint if configured
        checkpoint_interval = self.config.get("checkpoint_interval", 5)
        if generation % checkpoint_interval == 0:
            self._save_checkpoint()

        # Update run status
        if self._stop_requested or self.should_stop():
            self.run.status = EvolutionStatus.COMPLETED if not self._paused else EvolutionStatus.PAUSED
            self._running = False

        stats = self.grid.get_statistics()
        stats["generation"] = generation
        stats["new_variants"] = len(new_variants)
        stats["best_fitness"] = self.run.best_fitness

        return stats

    async def run_evolution(self) -> EvolutionRun:
        """
        Run the complete evolution loop.

        Returns:
            Completed evolution run
        """
        if not self.run or not self.grid:
            raise RuntimeError("Evolution not started")

        self.logger.info(
            "Starting evolution loop",
            run_id=self.run.id,
            max_generations=self.run.max_generations,
        )

        try:
            while self._running and not self.should_stop():
                # Check for pause
                while self._paused:
                    await asyncio.sleep(0.1)
                    if self._stop_requested:
                        break

                if self._stop_requested:
                    break

                # Evolve one generation
                await self.evolve_generation()

                # Small delay to prevent tight loop
                await asyncio.sleep(0.01)

        except Exception as e:
            self.logger.error(f"Evolution error: {e}")
            self.run.status = EvolutionStatus.FAILED

        finally:
            self.run.end_time = datetime.utcnow()
            self._running = False

            # Save final checkpoint
            self._save_checkpoint()

            self.logger.info(
                "Evolution completed",
                run_id=self.run.id,
                generations=self.run.current_generation,
                best_fitness=self.run.best_fitness,
                duration=self.run.duration(),
            )

        return self.run

    def should_stop(self) -> bool:
        """
        Check if evolution should stop.

        Returns:
            True if stopping criteria met
        """
        if not self.run:
            return True

        # Max generations reached
        if self.run.current_generation >= self.run.max_generations:
            self.logger.info("Max generations reached")
            return True

        # Convergence check (grid fully covered)
        if self.grid and self.grid.get_coverage() >= 0.95:
            self.logger.info("Grid coverage threshold reached")
            return True

        return False

    def pause(self) -> None:
        """Pause the evolution."""
        if not self._running:
            return

        self._paused = True
        self.run.status = EvolutionStatus.PAUSED
        self.logger.info("Evolution paused", run_id=self.run.id)

    def resume(self) -> None:
        """Resume the evolution."""
        if not self._paused:
            return

        self._paused = False
        self.run.status = EvolutionStatus.RUNNING
        self.logger.info("Evolution resumed", run_id=self.run.id)

    def stop(self) -> None:
        """Stop the evolution."""
        self._stop_requested = True
        self.logger.info("Evolution stop requested", run_id=self.run.id)

    def get_statistics(self) -> Dict:
        """
        Get current evolution statistics.

        Returns:
            Dictionary with statistics
        """
        if not self.run:
            return {"status": "not_started"}

        stats = {
            "run_id": self.run.id,
            "tool_name": self.run.target_tool_name,
            "status": self.run.status.value,
            "current_generation": self.run.current_generation,
            "max_generations": self.run.max_generations,
            "best_fitness": self.run.best_fitness,
            "duration_seconds": self.run.duration(),
        }

        if self.grid:
            stats.update(self.grid.get_statistics())

        if self.evaluator:
            stats["evaluations_cached"] = self.evaluator.cache_size()

        return stats

    def get_elites(self) -> List[EvolvedCode]:
        """
        Get all elite solutions.

        Returns:
            List of evolved codes sorted by fitness
        """
        if not self.grid:
            return []

        return self.grid.get_elites()

    def get_best(self) -> Optional[EvolvedCode]:
        """
        Get the best solution.

        Returns:
            Best evolved code or None
        """
        if not self.grid:
            return None

        return self.grid.get_best()

    def _save_checkpoint(self) -> None:
        """Save current state as checkpoint."""
        if not self.run or not self.grid or not self.checkpoint_manager:
            return

        # Save grid
        grid_data = self.grid.to_dict()

        # Save run
        run_data = self.run.to_dict()

        self.checkpoint_manager.save_checkpoint(
            self.run.id,
            self.run.current_generation,
            grid_data,
            run_data,
        )

    def is_running(self) -> bool:
        """Check if evolution is currently running."""
        return self._running

    def is_paused(self) -> bool:
        """Check if evolution is paused."""
        return self._paused
