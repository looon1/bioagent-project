# BioAgent

> **Version 2.0 - Phase 2 Complete** 🎉

A minimalist, modular biomedical AI agent framework built on learnings from PantheonOS, Biomni, and Claude Code.

## Features

### Core Features
- **Minimalist Design**: Simple starting point, easy to debug
- **Modular Architecture**: Tool/prompt/skills separation with hot-pluggable interfaces
- **Multiple LLM Support**: OpenAI, Anthropic Claude, and custom endpoints (Zhipu GLM)
- **Full Observability**: Comprehensive logging, metrics, and cost tracking
- **Biomedical Tools**: UniProt, Gene Ontology, PubMed, and more

### Phase 2 Features (✅ Completed)
- **External Tool Integration**: Biomni adapter for 105+ biomedical tools
- **Multi-Agent Teams**: Sequential, Hierarchical, Agent-as-Tool, and Swarm patterns
- **Unified API**: Consistent interfaces across all components
- **Domain Management**: Enable/disable tools by domain

## Quick Start

```bash
# Install dependencies
pip install -e .

# Set environment variables
export MODEL_ID=glm-4.7
export ZHIPU_API_KEY=your_api_key_here
export BIOAGENT_LOGS_PATH=./logs

# Run the agent
python -m bioagent.cli "查询 TP53 基因的功能"
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
│   │   └── team.py    # Team patterns
│   ├── tools/         # Tool registry and implementations
│   │   ├── registry.py
│   │   ├── loader.py
│   │   ├── adapter.py  # Phase 2: External tool integration
│   │   ├── core/
│   │   │   ├── database.py   # UniProt, Gene, PubMed
│   │   │   ├── analysis.py
│   │   │   └── files.py
│   │   └── base.py
│   ├── observability/ # Logging, metrics, cost tracking
│   └── prompts/      # System prompts
├── docs/             # Documentation
│   ├── PROJECT_REQUIREMENTS.md
│   ├── GETTING_STARTED.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── PROGRESS_CHECKLIST.md
├── scripts/          # Utility scripts
│   ├── run_bioagent.py
│   ├── test_bioagent.py
│   ├── test_phase2.py        # Phase 2 tests
│   ├── test_phase2_fixed.py  # Unified API tests
│   └── test_phase2_questions.py  # Question-based tests
├── tests/           # Test files
│   └── test_phase2.py
├── examples/         # Usage examples
├── data/            # Data files
├── logs/            # Log files
├── README.md
├── CLAUDE.md        # Claude Code instructions
├── PHASE2_SUMMARY.md        # Phase 2 summary
├── PHASE2_API_UNIFICATION.md # API unification report
└── pyproject.toml
```

## Configuration

### Core Configuration

Set the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `MODEL_ID` | LLM model to use | Required |
| `ZHIPU_API_KEY` | API key for Zhipu AI | Required |
| `ANTHROPIC_API_KEY` | API key for Claude | Optional |
| `BIOAGENT_LOGS_PATH` | Path for log files | `./logs` |
| `BIOAGENT_BASE_URL` | Custom API endpoint | `None` |

### Phase 2 Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `BIOAGENT_ENABLE_BIOMNI` | Enable Biomni tools | `false` |
| `BIOAGENT_BIOMNI_PATH` | Path to Biomni installation | `None` |
| `BIOAGENT_BIOMNI_DOMAINS` | Biomni domains to load | `None` |
| `BIOAGENT_ENABLE_MULTI_AGENT` | Enable multi-agent mode | `false` |
| `BIOAGENT_AGENT_TEAM_MODE` | Team mode | `"single"` |

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

### Biomni Tools (Phase 2)
When `BIOAGENT_ENABLE_BIOMNI=true`, get access to 105+ biomedical tools:
- Genetics, Genomics, Cancer Biology, Cell Biology
- Biochemistry, Biophysics, Immunology
- Database operations, Literature mining

## Multi-Agent Patterns (Phase 2)

## Development

### Running Tests

```bash
# Core tests
python scripts/test_bioagent.py

# Phase 2 tests
python scripts/test_phase2.py

# Unified API tests (100% pass rate)
python scripts/test_phase2_fixed.py

# Question-based tests
python scripts/test_phase2_questions.py
```

### Multi-Agent Examples (Phase 2)

#### Sequential Team
```python
from bioagent.agents import SequentialTeam

agent1 = Agent(config=config)
agent2 = Agent(config=config)

team = SequentialTeam([agent1, agent2], connect_prompt="Continue:")
result = await team.execute("Analyze this dataset")
```

#### Hierarchical Team
```python
from bioagent.agents import HierarchicalTeam

supervisor = Agent(config=config)
specialists = [Agent(config=config) for _ in range(3)]

team = HierarchicalTeam(supervisor, specialists)
result = await team.execute("Perform analysis")
```

#### Biomni Integration
```python
config = BioAgentConfig.from_env()
config.enable_biomni_tools = True
config.biomni_domains = ["genetics", "genomics"]

agent = Agent(config=config)
result = await agent.execute("Perform gene enrichment analysis")
```

### Adding New Tools

```python
from bioagent.tools.base import tool

@tool(domain="mydomain")
async def my_tool(param1: str, param2: int) -> Dict[str, Any]:
    """
    Tool description.

    Args:
        param1: Description
        param2: Description

    Returns:
        Dictionary with results
    """
    # Implementation
    return {"result": "..."}
```

## Documentation

- [Project Requirements](docs/PROJECT_REQUIREMENTS.md) - Detailed requirements and design
- [Getting Started](docs/GETTING_STARTED.md) - Setup and usage guide
- [Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md) - Architecture overview
- [Progress Checklist](docs/PROGRESS_CHECKLIST.md) - Development status
- [Phase 2 Summary](PHASE2_SUMMARY.md) - Phase 2 implementation details
- [API Unification Report](PHASE2_API_UNIFICATION.md) - API consistency documentation
- [CLAUDE.md](CLAUDE.md) - Claude Code development guide

## License

MIT

## References

This project draws inspiration from:

- [PantheonOS](https://github.com/aristoteleo/PantheonOS) - Multi-agent architecture
- [Biomni](https://github.com/snap-stanford/Biomni) - Tool management patterns
- [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code/) - Skills system design
