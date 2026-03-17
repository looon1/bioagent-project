# BioAgent Evolution System

Phase 10 of the BioAgent project implements a code evolution system inspired by PantheonOS, adapted for biomedical AI agents. This system enables automatic improvement and optimization of tools through quality-diversity optimization.

## Overview

The evolution system combines:
- **MAP-Elites Algorithm**: Quality-diversity optimization that maintains diverse solutions across a behavior space
- **Hybrid Evaluation**: Combines functional tests with LLM-based code quality assessment
- **Mutation Strategies**: Multiple approaches to generating code variants
- **Checkpoint/Resume**: State persistence for long-running evolution experiments

## Architecture

### Core Components

```
bioagent/evolution/
├── __init__.py          # Package exports
├── models.py            # Data models (EvolutionRun, EvolvedCode, FitnessScore)
├── engine.py            # EvolutionEngine main coordinator
├── grid.py             # MAP-Elites grid implementation
├── evaluator.py         # HybridEvaluator (function + LLM feedback)
├── strategies.py        # Mutation strategies (analyzer-mutator pattern)
├── checkpoint.py        # CheckpointManager for state persistence
└── tools.py            # Evolution tools for agent integration
```

### Data Flow

```
Base Code
    ↓
EvolutionEngine
    ↓
Mutation Strategies → Generate Variants
    ↓
Hybrid Evaluator
    ├── Functional Tests → Score 1
    └── LLM Feedback → Score 2
    ↓
Fitness Score (Weighted Combination)
    ↓
MAP-Elites Grid (Behavior Space)
    ↓
Best Solutions → Promotion to Tool Registry
```

## Configuration

### Enable Evolution

```python
from bioagent.config import BioAgentConfig
from bioagent.agent import Agent

# Enable evolution system
config = BioAgentConfig.from_env()
config.enable_evolution = True
config.evolution_max_generations = 50
config.evolution_population_size = 20
config.evolution_grid_resolution = 10

agent = Agent(config=config)
```

### Environment Variables

| Variable | Description | Default |
|-----------|-------------|----------|
| `BIOAGENT_ENABLE_EVOLUTION` | Enable evolution system | false |
| `BIOAGENT_EVOLUTION_DIR` | Directory for evolution storage | .evolution |
| `BIOAGENT_EVOLUTION_MAX_GENERATIONS` | Max generations per run | 50 |
| `BIOAGENT_EVOLUTION_POPULATION_SIZE` | Population size | 20 |
| `BIOAGENT_EVOLUTION_GRID_RESOLUTION` | MAP-Elites grid resolution | 10 |
| `BIOAGENT_EVOLUTION_MUTATION_RATE` | Mutation probability | 0.3 |
| `BIOAGENT_EVOLUTION_CROSSOVER_RATE` | Crossover probability | 0.5 |
| `BIOAGENT_EVOLUTION_FUNCTIONAL_WEIGHT` | Weight for functional tests | 0.6 |
| `BIOAGENT_EVOLUTION_LLM_WEIGHT` | Weight for LLM quality | 0.4 |
| `BIOAGENT_EVOLUTION_CHECKPOINT_INTERVAL` | Generations per checkpoint | 5 |
| `BIOAGENT_EVOLUTION_MAX_CHECKPOINTS` | Max checkpoints to keep | 10 |
| `BIOAGENT_EVOLUTION_TARGET_TOOLS` | Tools to evolve (comma-separated) | - |
| `BIOAGENT_EVOLUTION_RESUME_FROM` | Checkpoint to resume from | - |

## Evolution Tools

When evolution is enabled, the agent gains access to evolution management tools:

### `start_evolution`

Start a new evolution run for a tool.

```python
result = await agent.execute(
    "Start evolution for the query_uniprot tool with max 100 generations"
)
```

Parameters:
- `tool_name`: Name of the tool to evolve
- `base_code`: Starting Python code for the tool
- `max_generations`: Maximum number of generations (default: 50)
- `population_size`: Number of variants per generation (default: 20)
- `grid_resolution`: MAP-Elites grid resolution (default: 10)
- `mutation_rate`: Probability of mutation (0-1, default: 0.3)
- `test_cases`: Optional list of test case dicts
- `run_async`: Run evolution in background (default: False)

### `evolve_tool`

Evolve a specific tool using its current code.

```python
result = await agent.execute(
    "Evolve the query_gene tool to improve its performance"
)
```

### `get_evolution_status`

Check progress of evolution runs.

```python
result = await agent.execute(
    "Get the status of all active evolution runs"
)
```

### `pause_evolution` / `resume_evolution`

Control evolution run lifecycle.

```python
result = await agent.execute(
    "Pause the evolution run with ID evolution_query_uniprot_20260318_120000"
)
```

### `get_evolved_tool`

Retrieve best evolved versions.

```python
result = await agent.execute(
    "Get the top 5 evolved solutions from run evolution_query_uniprot_20260318_120000"
)
```

Parameters:
- `run_id`: ID of the evolution run
- `get_best`: If True, return only the best solution (default: True)
- `top_k`: If specified, return top k elite solutions

### `promote_evolved_tool`

Promote an evolved tool to the agent's tool registry.

```python
result = await agent.execute(
    "Promote the best evolved solution from evolution_query_uniprot_20260318_120000"
)
```

### `list_evolution_runs`

List all evolution runs (active and completed).

```python
result = await agent.execute(
    "List all evolution runs and their status"
)
```

## Mutation Strategies

### Analyzer-Mutator Strategy

Two-stage mutation:
1. **Analyzer**: LLM analyzes code and identifies improvement opportunities
2. **Mutator**: LLM generates code based on analyzer recommendations

Best for: Finding and fixing bugs, improving correctness

### Code Rewriter Strategy

Direct LLM code rewriting:
- LLM directly rewrites code with specific mutation guidance
- Focused improvements: efficiency, readability, error handling

Best for: General code improvements, refactoring

### Parameter Tuner Strategy

Hyperparameter optimization:
- Identifies tunable parameters in code
- Adjusts parameter values within bounds
- Preserves code structure

Best for: Optimizing numeric constants and thresholds

## Fitness Evaluation

### Composite Fitness Score

```
fitness = 0.6 * functional_score
        + 0.35 * llm_quality_score
        + 0.05 * diversity_bonus
```

### Functional Score (0-1)

Based on test case execution:
- Pass/fail ratio of test cases
- Edge case handling
- Error recovery

### LLM Quality Score (0-1)

Based on LLM assessment:
- Correctness: Does code implement expected behavior?
- Readability: Is code clear and well-structured?
- Efficiency: Is code reasonably efficient?
- Safety: Does code follow best practices?

### Diversity Bonus (0-1)

Reward for novel behaviors:
- Inverse of similarity to existing solutions
- Encourages exploration of behavior space

## MAP-Elites Grid

The MAP-Elites algorithm maintains a grid of elite solutions across behavior space:

- **Behavior Space**: 7-dimensional space characterizing code behavior
  - Code complexity (normalized LOC)
  - Uses lists, dicts, async
  - Behavior type (math, I/O, network)

- **Grid Cells**: Each cell contains the best solution for that region
- **Insertion**: New solution replaces existing if fitness is higher
- **Coverage**: Percentage of grid cells with solutions

## Checkpoint System

Evolution runs can be saved and resumed:

```python
# Checkpoints saved automatically every N generations
# Default: every 5 generations

# Resume from checkpoint
config = BioAgentConfig.from_env()
config.evolution_resume_from = "path/to/checkpoint.json"

agent = Agent(config=config)
```

## Testing

Run the evolution system test suite:

```bash
python scripts/test_phase10_evolution.py
```

Tests cover:
- Evolution data models
- MAP-Elites grid operations
- Hybrid evaluation
- Mutation strategies
- Checkpoint system
- Evolution engine
- Agent integration

## Best Practices

1. **Define Good Test Cases**: Provide comprehensive test cases for meaningful evaluation

2. **Choose Appropriate Parameters**:
   - `max_generations`: Start with 10-20 for testing, 50-100 for production
   - `population_size`: 10-30 for most scenarios
   - `grid_resolution`: 10 for 7D space, adjust for custom dimensions

3. **Monitor Progress**: Use `get_evolution_status` to track evolution

4. **Review Results**: Compare elite solutions before promoting

5. **Use Checkpoints**: Enable checkpointing for long runs to avoid losing progress

## Example Use Cases

### Evolving a Database Query Tool

```python
# Starting code
base_code = """
def query_database(protein_id):
    url = f"https://api.uniprot.org/uniprot/{protein_id}.json"
    import requests
    response = requests.get(url)
    return response.json()
"""

# Start evolution
result = start_evolution(
    tool_name="query_database",
    base_code=base_code,
    max_generations=20,
    test_cases=[
        {"input": "query_database('TP53')", "expected": {"uniprot_id": "TP53"}},
        {"input": "query_database('INS')", "expected": {"uniprot_id": "INS"}},
    ],
    agent=agent,
)
```

### Continuous Improvement

Evolution can be used iteratively to continuously improve tools:

1. Run evolution for N generations
2. Review elite solutions
3. Promote best solution
4. Use promoted solution as new base for next evolution run

## Integration Points

- **Agent System**: Evolution tools available when `enable_evolution=True`
- **Tool Registry**: Evolved tools can be registered/promoted
- **LLM Provider**: Uses existing `LLMProvider` for code generation
- **Background Tasks**: Long evolution runs can run as background tasks
- **Observability**: Metrics logged via `Logger`

## Limitations

1. **Evaluation Cost**: LLM-based evaluation requires API calls
2. **Code Complexity**: Complex tools may require more generations
3. **Test Coverage**: Quality depends on test case coverage
4. **Behavior Space**: Fixed 7D space may not capture all behaviors

## Future Enhancements

- Adaptive mutation rates based on generation progress
- Custom behavior space definition
- Multi-objective optimization
- Parallel evolution of multiple tools
- Evolution history visualization
