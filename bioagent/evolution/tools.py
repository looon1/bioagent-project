"""
Evolution tools for agent integration.

Provides tools that agents can use to start, monitor, and manage evolution runs.
"""

import asyncio
from typing import Any, Dict, List, Optional

from bioagent.evolution.engine import EvolutionEngine
from bioagent.evolution.models import EvolutionRun, EvolvedCode, EvolutionStatus
from bioagent.observability import Logger


# Global registry for active evolution engines
_active_engines: Dict[str, EvolutionEngine] = {}


def start_evolution(
    tool_name: str,
    base_code: str,
    max_generations: int = 50,
    population_size: int = 20,
    grid_resolution: int = 10,
    mutation_rate: float = 0.3,
    test_cases: Optional[List[Dict]] = None,
    evolution_dir: str = ".evolution",
    run_async: bool = False,
    agent: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Start a new evolution run for a tool.

    Use this tool to evolve and improve tool implementations.

    Args:
        tool_name: Name of the tool to evolve
        base_code: Starting Python code for the tool
        max_generations: Maximum number of generations (default: 50)
        population_size: Number of variants per generation (default: 20)
        grid_resolution: MAP-Elites grid resolution (default: 10)
        mutation_rate: Probability of mutation (0-1, default: 0.3)
        test_cases: Optional list of test case dicts with "input" and "expected"
        evolution_dir: Directory for storing evolution data
        run_async: Run evolution in background (default: False)
        agent: Agent instance for accessing LLM provider

    Returns:
        Dictionary with evolution run ID and initial status
    """
    if agent is None:
        return {"error": "Agent instance required for evolution"}

    # Extract LLM provider and logger from agent
    llm_provider = agent.llm
    logger = agent.logger

    # Configuration
    config = {
        "max_generations": max_generations,
        "population_size": population_size,
        "grid_resolution": grid_resolution,
        "mutation_rate": mutation_rate,
        "evolution_dir": evolution_dir,
        "test_cases": test_cases,
    }

    # Create engine
    engine = EvolutionEngine(config, llm_provider, logger)

    # Start evolution
    async def _start():
        run = await engine.start_evolution(tool_name, base_code, test_cases)

        # Store engine
        _active_engines[run.id] = engine

        # Run async if requested
        if run_async:
            asyncio.create_task(engine.run_evolution())
            return run.to_dict()
        else:
            completed = await engine.run_evolution()
            return completed.to_dict()

    # Run in event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(_start())

    return result


def evolve_tool(
    tool_name: str,
    max_generations: int = 50,
    population_size: int = 20,
    evolution_dir: str = ".evolution",
    agent: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Evolve a specific tool using its current code.

    This tool extracts the current code for a tool and evolves it.

    Args:
        tool_name: Name of the tool to evolve
        max_generations: Maximum number of generations (default: 50)
        population_size: Number of variants per generation (default: 20)
        evolution_dir: Directory for storing evolution data
        agent: Agent instance for accessing tools

    Returns:
        Dictionary with evolution results
    """
    if agent is None:
        return {"error": "Agent instance required"}

    # Get tool from registry
    tool = agent.tool_registry.get_tool(tool_name)
    if not tool:
        return {"error": f"Tool '{tool_name}' not found"}

    # Extract code
    import inspect
    base_code = inspect.getsource(tool.function)

    # Start evolution
    return start_evolution(
        tool_name=tool_name,
        base_code=base_code,
        max_generations=max_generations,
        population_size=population_size,
        evolution_dir=evolution_dir,
        run_async=True,
        agent=agent,
    )


def get_evolution_status(
    run_id: Optional[str] = None,
    agent: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Get status of evolution runs.

    Args:
        run_id: Optional specific run ID to check
        agent: Agent instance for accessing evolution manager

    Returns:
        Dictionary with evolution status information
    """
    if not _active_engines:
        return {"status": "no_active_runs", "active_engines": []}

    if run_id:
        # Get specific run
        engine = _active_engines.get(run_id)
        if not engine:
            return {"error": f"Run '{run_id}' not found"}

        return {
            "run_id": run_id,
            **engine.get_statistics(),
        }
    else:
        # Get all runs
        runs = []
        for rid, engine in _active_engines.items():
            runs.append({
                "run_id": rid,
                **engine.get_statistics(),
            })

        return {
            "active_engines": len(runs),
            "runs": runs,
        }


def pause_evolution(run_id: str) -> Dict[str, Any]:
    """
    Pause an active evolution run.

    Args:
        run_id: ID of the evolution run to pause

    Returns:
        Status message
    """
    engine = _active_engines.get(run_id)
    if not engine:
        return {"error": f"Run '{run_id}' not found"}

    engine.pause()
    return {
        "run_id": run_id,
        "status": "paused",
        "message": f"Evolution run {run_id} paused"
    }


def resume_evolution(run_id: str) -> Dict[str, Any]:
    """
    Resume a paused evolution run.

    Args:
        run_id: ID of the evolution run to resume

    Returns:
        Status message
    """
    engine = _active_engines.get(run_id)
    if not engine:
        return {"error": f"Run '{run_id}' not found"}

    engine.resume()

    # Start running again if not already running
    if not engine.is_running():
        asyncio.create_task(engine.run_evolution())

    return {
        "run_id": run_id,
        "status": "resumed",
        "message": f"Evolution run {run_id} resumed"
    }


def get_evolved_tool(
    run_id: str,
    get_best: bool = True,
    top_k: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get evolved tool code from an evolution run.

    Args:
        run_id: ID of the evolution run
        get_best: If True, return only the best solution (default: True)
        top_k: If specified, return top k elite solutions

    Returns:
        Dictionary with evolved tool code and metadata
    """
    engine = _active_engines.get(run_id)
    if not engine:
        return {"error": f"Run '{run_id}' not found"}

    if get_best:
        best = engine.get_best()
        if not best:
            return {"error": "No evolved solutions found"}

        return {
            "run_id": run_id,
            "rank": 1,
            "fitness": best.fitness.combined,
            "code": best.code,
            "generation": best.generation,
            "mutation_type": best.mutation_type.value,
            "llm_feedback": best.llm_feedback,
        }

    elites = engine.get_elites()
    if not elites:
        return {"error": "No evolved solutions found"}

    if top_k:
        elites = elites[:top_k]

    results = []
    for i, evolved in enumerate(elites, 1):
        results.append({
            "rank": i,
            "id": evolved.id,
            "fitness": evolved.fitness.combined,
            "code": evolved.code,
            "generation": evolved.generation,
            "mutation_type": evolved.mutation_type.value,
            "llm_feedback": evolved.llm_feedback,
        })

    return {
        "run_id": run_id,
        "solutions": results,
        "total": len(results),
    }


def list_evolution_runs(
    agent: Optional[Any] = None
) -> Dict[str, Any]:
    """
    List all evolution runs (active and completed).

    Args:
        agent: Agent instance for accessing checkpoint manager

    Returns:
        Dictionary with evolution run information
    """
    # Get active runs
    active_runs = []
    for run_id, engine in _active_engines.items():
        stats = engine.get_statistics()
        active_runs.append({
            "run_id": run_id,
            "status": stats["status"],
            "current_generation": stats.get("current_generation", 0),
            "best_fitness": stats.get("best_fitness", 0.0),
        })

    # Get completed runs from checkpoints
    completed_runs = []
    if agent:
        try:
            from bioagent.evolution.checkpoint import CheckpointManager
            evolution_dir = agent.config.evolution_dir if hasattr(agent.config, 'evolution_dir') else ".evolution"
            checkpoint_manager = CheckpointManager(evolution_dir, agent.logger)

            for checkpoint in checkpoint_manager.list_checkpoints():
                if checkpoint["run_id"] not in [r["run_id"] for r in active_runs]:
                    completed_runs.append({
                        "run_id": checkpoint["run_id"],
                        "generation": checkpoint["generation"],
                        "timestamp": checkpoint["timestamp"],
                    })

        except Exception as e:
            pass  # Skip checkpoint loading if it fails

    return {
        "active_runs": len(active_runs),
        "completed_runs": len(completed_runs),
        "runs": active_runs + completed_runs,
    }


def promote_evolved_tool(
    run_id: str,
    rank: int = 1,
    agent: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Promote an evolved tool to the agent's tool registry.

    Args:
        run_id: ID of the evolution run
        rank: Rank of solution to promote (1 = best)
        agent: Agent instance for tool registration

    Returns:
        Status message
    """
    if agent is None:
        return {"error": "Agent instance required"}

    # Get evolved solution
    solution = get_evolved_tool(run_id, get_best=(rank == 1), top_k=rank)
    if "error" in solution:
        return solution

    # Extract code
    if get_best:
        code = solution["code"]
    else:
        code = solution["solutions"][rank - 1]["code"]

    # Execute the code to get the function
    namespace = {}
    try:
        exec(code, namespace)

        # Find the function
        func = None
        for name, value in namespace.items():
            if callable(value) and not name.startswith("_"):
                func = value
                break

        if func is None:
            return {"error": "Could not extract function from evolved code"}

        # Register with agent
        agent.register_tool(func)

        return {
            "run_id": run_id,
            "rank": rank,
            "status": "promoted",
            "message": f"Evolved tool (rank {rank}) registered successfully",
        }

    except Exception as e:
        return {"error": f"Failed to register evolved tool: {e}"}


def clear_evolution_cache(run_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Clear evolution engine cache.

    Args:
        run_id: Optional specific run ID to clear

    Returns:
        Status message
    """
    cleared = 0

    if run_id:
        engine = _active_engines.get(run_id)
        if engine and engine.evaluator:
            engine.evaluator.clear_cache()
            cleared = 1
    else:
        for engine in _active_engines.values():
            if engine.evaluator:
                engine.evaluator.clear_cache()
                cleared += 1

    return {
        "status": "cleared",
        "engines_cleared": cleared,
        "message": f"Cleared evaluation cache for {cleared} engine(s)",
    }
