# BioAgent

> **Version 3.0 - All Phases Complete** 🎉

A minimalist, modular biomedical AI agent framework built on learnings from PantheonOS, Biomni, and Claude Code.

BioAgent implements a ReAct-style agent with tool calling capabilities, specialized for biomedical research tasks. The framework supports multiple LLM providers (OpenAI, Anthropic Claude, custom endpoints like Zhipu GLM) and now includes comprehensive features across 10 development phases.

## Features

### Core Features (Phase 1)
- **Minimalist Design**: Simple starting point, easy to debug
- **Modular Architecture**: Tool/prompt/skills separation with hot-pluggable interfaces
- **Multiple LLM Support**: OpenAI, Anthropic Claude, and custom endpoints (Zhipu GLM)
- **Full Observability**: Comprehensive logging, metrics, and cost tracking
- **Biomedical Tools**: UniProt, Gene Ontology, PubMed, and more

### Multi-Agent Teams (Phase 2)
- **External Tool Integration**: Biomni adapter for 105+ biomedical tools
- **Multi-Agent Patterns**: Sequential, Hierarchical, Agent-as-Tool, and Swarm teams
- **Unified API**: Consistent interfaces across all components
- **Domain Management**: Enable/disable tools by domain
- **Automatic Delegation**: Task complexity-based multi-agent selection

### Task System (Phase 4)
- **TodoWrite**: Plan and track multi-step work
- **TaskManager**: JSON-based persistence with dependency management
- **Auto-resolve**: Automatic dependency resolution when tasks complete
- **Task Lifecycle**: Pending → In Progress → Completed/Failed

### Background Tasks (Phase 5)
- **Async Execution**: Long-running operations without blocking
- **Output Capture**: Reliable stdout/stderr buffering
- **Status Tracking**: Monitor progress of background operations
- **Completion Queue**: Receive notifications when tasks finish

### Context Management (Phase 6)
- **Three-Layer Compression**: History summarization, result compression, prompt optimization
- **Micro-Compact**: Keep recent tool results
- **Auto-Compact**: Trigger on token threshold
- **Manual-Compact`: User-triggered compression with focus

### Advanced Team Protocols (Phase 7)
- **JSONL Mailbox**: Request-response pattern between agents
- **Autonomous Agents**: Idle polling, task kanban, auto-claim
- **Health Monitoring**: Peer health checks and reconnection
- **Team Discovery**: Dynamic agent registration and lookup

### Worktree Isolation (Phase 8)
- **Git Worktree**: Directory-level task isolation
- **Task Binding**: Associate worktrees with task IDs
- **Safe Execution**: Run commands in isolated environments
- **Lifecycle Management**: Create, list, run, keep, remove worktrees

### Web UI (Phase 9)
- **FastAPI Backend**: Server-sent events for streaming
- **Session Management**: Track conversations and history
- **CLI Tool**: `bioagent-web` command for starting server
- **Real-time**: Stream responses to web interface

### Code Evolution (Phase 10) 🆕
- **MAP-Elites Grid**: Quality-diversity optimization
- **Hybrid Evaluation**: Functional tests + LLM quality assessment
- **Mutation Strategies**: Analyzer-Mutator, Code Rewriter, Parameter Tuner
- **Checkpoint/Resume**: State persistence for long runs
- **Evolution Tools**: 9 tools for managing evolution runs

## Quick Start

```bash
# Install dependencies
pip install -e .

# Set environment variables
export ANTHROPIC_API_KEY=your_api_key_here
# or for Zhipu GLM:
# export ZHIPU_API_KEY=your_api_key_here
# export BIOAGENT_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4

# Run the agent
python -m bioagent.cli "query TP53 gene function"

# Interactive mode
python -m bioagent.cli -i

# Start Web UI
python -m bioagent.web.cli
```

## Project Structure

```
bioagent-project/
├── bioagent/           # Source code
│   ├── agent.py        # Main agent implementation
│   ├── llm.py         # LLM provider abstraction
│   ├── config.py       # Configuration management
│   ├── state.py       # Agent state tracking
│   ├── cli.py         # Command-line interface
│   ├── agents/        # Phase 2: Multi-agent teams
│   │   ├── __init__.py
│   │   ├── team.py     # Team patterns
│   │   ├── factory.py  # Simple agent factory
│   │   └── analyzer.py # Task complexity analyzer
│   ├── tools/         # Tool registry and implementations
│   │   ├── registry.py
│   │   ├── loader.py
│   │   ├── adapter.py  # Phase 2: External tool integration
│   │   ├── core/
│   │   │   ├── database.py   # UniProt, Gene, PubMed
│   │   │   ├── analysis.py   # Python code execution
│   │   │   ├── files.py      # File operations
│   │   │   └── background.py # Background task tools
│   │   └── base.py
│   ├── tasks/         # Phase 4: Task system
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   └── todo.py
│   ├── background/     # Phase 5: Background tasks
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   └── capture.py
│   ├── context/       # Phase 6: Context management
│   │   ├── __init__.py
│   │   └── manager.py
│   ├── team/          # Phase 7: Team protocols
│   │   ├── __init__.py
│   │   ├── protocol.py
│   │   ├── autonomous.py
│   │   ├── kanban.py
│   │   └── discovery.py
│   ├── worktree/      # Phase 8: Worktree isolation
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   ├── isolation.py
│   │   └── coordinator.py
│   ├── web/           # Phase 9: Web UI
│   │   ├── __init__.py
│   │   ├── server.py
│   │   └── cli.py
│   ├── evolution/      # Phase 10: Code evolution 🆕
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── engine.py
│   │   ├── grid.py
│   │   ├── evaluator.py
│   │   ├── strategies.py
│   │   ├── checkpoint.py
│   │   └── tools.py
│   ├── observability/ # Logging, metrics, cost tracking
│   └── prompts/      # System prompts
├── docs/             # Documentation
│   ├── evolution.md   # Phase 10: Evolution system guide 🆕
│   └── ...
├── scripts/          # Utility scripts
│   ├── test_phase10_evolution.py  # Phase 10 tests 🆕
│   └── ...
├── tests/           # Test files
├── examples/        # Usage examples
├── data/           # Data files
├── logs/           # Log files
├── .tasks/         # Task storage (Phase 4)
├── .transcripts/   # Context transcripts (Phase 6)
├── .teams/         # Team protocol storage (Phase 7)
├── .worktrees/     # Worktree storage (Phase 8)
├── .sessions/      # Web session storage (Phase 9)
├── .evolution/     # Evolution storage (Phase 10) 🆕
├── README.md
├── CLAUDE.md       # Claude Code instructions
├── BIOAGENT_ROADMAP.md  # Development roadmap
└── pyproject.toml
```

## Configuration

### Core Configuration

Set the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | API key for Claude | Required |
| `ZHIPU_API_KEY` | API key for Zhipu GLM | Optional |
| `BIOAGENT_MODEL` | LLM model to use | `claude-sonnet-4-20250514` |
| `BIOAGENT_BASE_URL` | Custom API endpoint | `None` |
| `BIOAGENT_LOGS_PATH` | Path for log files | `./bioagent_logs` |
| `BIOAGENT_LOG_LEVEL` | Logging level | `INFO` |

### Phase 4: Task System

| Variable | Description | Default |
|----------|-------------|---------|
| `BIOAGENT_ENABLE_TASK_TRACKING` | Enable task system | `true` |
| `BIOAGENT_TASKS_DIR` | Path for task storage | `./.tasks` |
| `BIOAGENT_AUTO_RESOLVE_DEPENDENCIES` | Auto-resolve dependencies | `true` |
| `BIOAGENT_TASK_COMPLETION_CLEANUP` | Auto-delete completed tasks | `true` |
| `BIOAGENT_TASK_RETENTION_DAYS` | Days to retain completed tasks | `7` |

### Phase 5: Background Tasks

| Variable | Description | Default |
|----------|-------------|---------|
| `BIOAGENT_ENABLE_BACKGROUND_TASKS` | Enable background tasks | `true` |
| `BIOAGENT_MAX_BACKGROUND_TASKS` | Max retained completed tasks | `50` |
| `BIOAGENT_BACKGROUND_TASK_TIMEOUT` | Default timeout (seconds) | `300` |

### Phase 6: Context Management

| Variable | Description | Default |
|----------|-------------|---------|
| `BIOAGENT_ENABLE_CONTEXT_COMPRESSION` | Enable context compression | `true` |
| `BIOAGENT_CONTEXT_MAX_TOKENS` | Token threshold for compression | `50000` |
| `BIOAGENT_COMPRESSION_THRESHOLD` | Compression ratio threshold | `0.8` |
| `BIOAGENT_CONTEXT_KEEP_RECENT` | Keep last N tool results | `3` |
| `BIOAGENT_TRANSCRIPTS_DIR` | Path for transcripts | `./.transcripts` |

### Phase 7: Team Protocols

| Variable | Description | Default |
|----------|-------------|---------|
| `BIOAGENT_TEAM_PROTOCOL` | Team protocol type | `sequential` |
| `BIOAGENT_TEAM_NAME` | Team name for protocol | `bioagent_team` |
| `BIOAGENT_TEAM_DIR` | Path for team storage | `./.teams` |
| `BIOAGENT_AUTONOMOUS_POLL_INTERVAL` | Poll interval (seconds) | `5.0` |
| `BIOAGENT_IDLE_TIMEOUT` | Idle timeout (seconds) | `60.0` |

### Phase 8: Worktree

| Variable | Description | Default |
|----------|-------------|---------|
| `BIOAGENT_ENABLE_WORKTREE` | Enable worktree system | `true` |
| `BIOAGENT_WORKTREES_DIR` | Path for worktree storage | `./.worktrees` |
| `BIOAGENT_WORKTREE_TIMEOUT` | Default timeout (seconds) | `300` |
| `BIOAGENT_WORKTREE_RETENTION_DAYS` | Days to retain removed worktrees | `7` |

### Phase 9: Web UI

| Variable | Description | Default |
|----------|-------------|---------|
| `BIOAGENT_WEB_HOST` | Host to bind server | `0.0.0.0` |
| `BIOAGENT_WEB_PORT` | Port for web server | `7860` |
| `BIOAGENT_ENABLE_CORS` | Enable CORS | `true` |
| `BIOAGENT_SESSIONS_DIR` | Path for session storage | `./.sessions` |

### Phase 10: Evolution 🆕

| Variable | Description | Default |
|----------|-------------|---------|
| `BIOAGENT_ENABLE_EVOLUTION` | Enable evolution system | `false` |
| `BIOAGENT_EVOLUTION_DIR` | Path for evolution storage | `./.evolution` |
| `BIOAGENT_EVOLUTION_MAX_GENERATIONS` | Max generations per run | `50` |
| `BIOAGENT_EVOLUTION_POPULATION_SIZE` | Population size | `20` |
| `BIOAGENT_EVOLUTION_GRID_RESOLUTION` | MAP-Elites grid resolution | `10` |
| `BIOAGENT_EVOLUTION_MUTATION_RATE` | Mutation probability | `0.3` |
| `BIOAGENT_EVOLUTION_FUNCTIONAL_WEIGHT` | Weight for functional tests | `0.6` |
| `BIOAGENT_EVOLUTION_LLM_WEIGHT` | Weight for LLM quality | `0.4` |
| `BIOAGENT_EVOLUTION_CHECKPOINT_INTERVAL` | Generations per checkpoint | `5` |
| `BIOAGENT_EVOLUTION_MAX_CHECKPOINTS` | Max checkpoints to keep | `10` |

## Available Tools

### Core Tools

| Tool | Domain | Description |
|------|--------|-------------|
| `query_uniprot` | database | Query UniProt protein database |
| `query_gene` | database | Query Gene Ontology API |
| `query_pubmed` | database | Search PubMed literature |
| `run_python_code` | analysis | Execute Python code |
| `read_file` | files | Read file contents |
| `write_file` | files | Write content to file |

### Task Tools (Phase 4)

| Tool | Domain | Description |
|------|--------|-------------|
| `create_task` | tasks | Create new task for tracking |
| `update_task` | tasks | Update task status or priority |
| `list_tasks` | tasks | List tasks with filtering |
| `get_task` | tasks | Get task details |

### Background Tools (Phase 5)

| Tool | Domain | Description |
|------|--------|-------------|
| `run_background` | background | Run tool in background |
| `check_background` | background | Check background task status |
| `cancel_background` | background | Cancel running task |

### Worktree Tools (Phase 8)

| Tool | Domain | Description |
|------|--------|-------------|
| `worktree_create` | worktree | Create new worktree |
| `worktree_list` | worktree | List all worktrees |
| `worktree_get` | worktree | Get worktree details |
| `worktree_status` | worktree | Show git status |
| `worktree_run` | worktree | Run command in worktree |
| `worktree_remove` | worktree | Remove worktree |
| `worktree_keep` | worktree | Mark worktree as kept |
| `worktree_events` | worktree | List recent events |
| `worktree_summary` | worktree | Get worktree statistics |

### Evolution Tools (Phase 10) 🆕

| Tool | Domain | Description |
|------|--------|-------------|
| `start_evolution` | evolution | Start new evolution run |
| `evolve_tool` | evolution | Evolve specific tool |
| `get_evolution_status` | evolution | Check evolution progress |
| `pause_evolution` | evolution | Pause evolution run |
| `resume_evolution` | evolution | Resume evolution run |
| `get_evolved_tool` | evolution | Retrieve evolved code |
| `list_evolution_runs` | evolution | List all runs |
| `promote_evolved_tool` | evolution | Promote to tool registry |
| `clear_evolution_cache` | evolution | Clear evaluation cache |

## Usage Examples

### Basic Agent Usage

```python
from bioagent.agent import Agent
from bioagent.config import BioAgentConfig

# Create agent
config = BioAgentConfig.from_env()
agent = Agent(config=config)

# Execute query
result = await agent.execute("Query TP53 gene function")
print(result)
```

### Multi-Agent Team

```python
from bioagent.agents import SequentialTeam

agent1 = Agent(config=config)
agent2 = Agent(config=config)

team = SequentialTeam([agent1, agent2], connect_prompt="Continue:")
result = await team.execute("Analyze this dataset")
```

### Task System

```python
# Create task
task_id = agent.create_agent_task(
    subject="Analyze protein data",
    description="Perform protein structure analysis",
    active_form="Analyzing protein data",
    priority="high"
)

# Update task
agent.update_agent_task(task_id, status="in_progress")
```

### Background Task

```python
# Run long operation in background
result = await agent.execute(
    "run_background with tool_name='long_analysis' and tool_args={'query': '...'}"
)
```

### Code Evolution 🆕

```python
# Enable evolution
config = BioAgentConfig.from_env()
config.enable_evolution = True
agent = Agent(config=config)

# Evolve a tool
result = await agent.execute(
    "Evolve the query_uniprot tool to improve performance"
)

# Check progress
result = await agent.execute(
    "Get evolution status for run evolution_query_uniprot_..."
)

# Promote best solution
result = await agent.execute(
    "Promote the best evolved solution from run evolution_query_uniprot_..."
)
```

## Development

### Running Tests

```bash
# Phase 10 evolution tests
python scripts/test_phase10_evolution.py
```

### Code Quality

```bash
# Format code with Black
black bioagent/

# Lint with Ruff
ruff check bioagent/

# Auto-fix Ruff issues
ruff check --fix bioagent/
```

## Documentation

- [CLAUDE.md](CLAUDE.md) - Claude Code development guide
- [BIOAGENT_ROADMAP.md](BIOAGENT_ROADMAP.md) - Complete development roadmap
- [docs/evolution.md](docs/evolution.md) - Evolution system guide 🆕

## Roadmap

All 10 phases are now complete:

- ✅ **Phase 1** - Agent Loop, Tool Use, Configuration, Observability
- ✅ **Phase 2** - Multi-Agent Teams, External Tool Integration
- ✅ **Phase 3** - Automatic Multi-Agent Delegation
- ✅ **Phase 4** - Task System
- ✅ **Phase 5** - Background Tasks
- ✅ **Phase 6** - Context Management
- ✅ **Phase 7** - Advanced Team Protocols
- ✅ **Phase 8** - Worktree Isolation
- ✅ **Phase 9** - Web UI
- ✅ **Phase 10** - Code Evolution

## License

MIT

## References

This project draws inspiration from:

- [PantheonOS](https://github.com/aristoteleo/PantheonOS) - Multi-agent architecture and evolution
- [Biomni](https://github.com/snap-stanford/Biomni) - Tool management patterns
- [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code/) - Skills system design
