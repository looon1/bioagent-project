# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**BioAgent v2.0 - Phase 2 Complete** 🎉

BioAgent is a minimalist, modular biomedical AI agent framework built using Python (>=3.9). It implements a ReAct-style agent with tool calling capabilities, specialized for biomedical research tasks. The framework supports multiple LLM providers (OpenAI, Anthropic Claude, custom endpoints like Zhipu GLM).

**Phase 2 Status: ✅ COMPLETED** (2026-03-17)
- ✅ External Tool Integration (Biomni adapter)
- ✅ Multi-Agent Team System
- ✅ Unified API Interface
- ✅ Comprehensive Testing (100% pass rate)
- ✅ API Unification across all components

## Development Commands

### Installation
```bash
pip install -e .
```

### Running Tests
```bash
python scripts/test_bioagent.py
# Or using pytest:
pytest tests/
```

### Linting and Formatting
```bash
# Format code with Black
black bioagent/

# Lint with Ruff
ruff check bioagent/

# Auto-fix Ruff issues
ruff check --fix bioagent/
```

### Running the Agent

CLI mode:
```bash
python -m bioagent.cli "query TP53 gene function"
python -m bioagent.cli -i  # Interactive mode
```

Python API:
```python
import asyncio
from bioagent.agent import Agent
from bioagent.config import BioAgentConfig

async def main():
    config = BioAgentConfig.from_env()
    agent = Agent(config=config)
    response = await agent.execute("Query UniProt for insulin protein")
    print(response)

asyncio.run(main())
```

## Architecture Overview

### Core Components

**Agent Execution Loop** (`bioagent/agent.py`)
- Implements ReAct pattern: Reasoning → Acting → Observing
- Main `Agent` class with `execute()` method handling the loop
- Manages conversation history, tool calls, and LLM interactions
- Supports max tool iterations (default: 10)
- Phase 2: Supports external tool integration via adapter

**Tool System** (`bioagent/tools/`)
- `@tool` decorator in `base.py` for marking functions as tools
- `ToolRegistry` for tool registration, lookup, and execution
- `ToolLoader` for dynamic tool loading from packages
- `ToolAdapter` - Phase 2: Base class for external tool integration
- `BiomniToolAdapter` - Phase 2: Specialized adapter for Biomni tools
- Tools are categorized by domain (e.g., "database", "analysis", "files", "genetics")

**LLM Abstraction** (`bioagent/llm.py`)
- `LLMProvider` abstract base class
- `OpenAIProvider` - works with OpenAI API and custom OpenAI-compatible endpoints (like Zhipu GLM)
- `AnthropicProvider` - for Claude models
- Factory function `get_llm_provider()` selects provider based on model name or base_url
- Provider selection: custom base_url → OpenAIProvider, "claude" in name → AnthropicProvider, "gpt"/"glm" → OpenAIProvider

**Configuration** (`bioagent/config.py`)
- `BioAgentConfig` dataclass with defaults
- Loads from environment variables via `from_env()` classmethod
- Required: `ANTHROPIC_API_KEY` (or `ZHIPU_API_KEY`/custom API key depending on provider)
- Optional: `BIOAGENT_MODEL`, `BIOAGENT_BASE_URL`, `BIOAGENT_LOGS_PATH`, etc.
- Phase 2: Added Biomni integration and multi-agent configuration options

**Observability** (`bioagent/observability/`)
- Structured logging with `Logger` (console + file output)
- `Metrics` for performance tracking (counters, gauges, timers)
- `CostTracker` for API cost calculation per model

**Multi-Agent Teams** (`bioagent/agents/`)
- Phase 2: Team-based agent composition patterns
- `Team` - Abstract base class for agent teams
- `SequentialTeam` - Sequential execution pattern
- `HierarchicalTeam` - Supervisor/delegation pattern
- `AgentAsToolTeam` - Agent-as-tool pattern
- `SwarmTeam` - Handoff-based pattern

### State Management

Agent state is tracked in `bioagent/state.py`:
- `AgentStatus` enum: IDLE, THINKING, EXECUTING_TOOL, COMPLETED, ERROR
- `AgentState` dataclass with messages, tool results, LLM calls
- Session metadata stored for tracking

## Adding New Tools

Create a new tool function with the `@tool` decorator:

```python
from bioagent.tools.base import tool

@tool(domain="mydomain")
async def my_tool(param1: str, param2: int) -> Dict[str, Any]:
    """
    Tool description here.

    Args:
        param1: Description
        param2: Description

    Returns:
        Dictionary with results
    """
    # Implementation
    return {"result": "..."}
```

Key points:
- Functions can be sync or async (both supported by registry)
- Parameters are auto-extracted for JSON Schema
- Domain categorization helps with tool filtering
- Docstring format for parameters should be `param_name: description`

Place new tool files in `bioagent/tools/core/` for core tools, or add new subdirectories under `bioagent/tools/` for domain-specific tools.

## Available Core Tools

| Tool | Domain | Description |
|------|--------|-------------|
| `query_uniprot` | database | Query UniProt protein database |
| `query_gene` | database | Query Gene Ontology API for gene information |
| `query_pubmed` | database | Search PubMed literature |
| `run_python_code` | analysis | Execute Python code safely |
| `read_file` | files | Read file contents |
| `write_file` | files | Write content to file |

## Phase 2: External Tool Integration

### Tool Adapter System (`bioagent/tools/adapter.py`)

BioAgent Phase 2 introduces a tool adapter system for integrating external tool libraries:

**ToolAdapter** - Base class for external tool integration:
- Load tools from external libraries (e.g., Biomni)
- Enable/disable tools by domain or individual tool
- Query available domains and enabled tools

**BiomniToolAdapter** - Specialized adapter for Biomni:
- Wraps Biomni functions as bioagent tools
- Preserves original tool descriptions
- Supports selective domain loading

### Multi-Agent Team System (`bioagent/agents/team.py`)

Team-based agent composition patterns inspired by PantheonOS:

**Team** - Abstract base class for agent teams:
- Manages multiple agents
- Provides agent lookup by session ID
- Defines common team interface

**SequentialTeam** - Sequential execution pattern:
- Agents execute in predefined order
- Connect prompt passes output between agents
- Pipeline-style processing

**HierarchicalTeam** - Supervisor/delegation pattern:
- Supervisor analyzes and delegates to sub-agents
- Supports feedback loops for improvement
- Dynamic agent selection based on task

**AgentAsToolTeam** - Agent-as-tool pattern:
- Sub-agents exposed as tools to leader
- Leader can call sub-agents dynamically
- Stores tool call results for reference

**SwarmTeam** - Handoff-based pattern:
- Dynamic agent handoffs during execution
- Memory maintains active agent state
- Up to 10 handoffs supported

### Biomni Integration

BioAgent can now integrate Biomni's 105+ biomedical tools:

```python
from bioagent.config import BioAgentConfig
from bioagent.agent import Agent

# Enable Biomni integration
config = BioAgentConfig.from_env()
config.enable_biomni_tools = True
config.biomni_path = "/path/to/biomni"
config.biomni_domains = ["genetics", "genomics"]

agent = Agent(config=config)

# Agent now has Biomni tools available
result = await agent.execute("Perform gene enrichment analysis")
```

Environment variables for Biomni:
- `BIOAGENT_ENABLE_BIOMNI` - Enable Biomni integration (true/false)
- `BIOAGENT_BIOMNI_PATH` - Path to Biomni installation
- `BIOAGENT_BIOMNI_DOMAINS` - Comma-separated list of domains (e.g., "genetics,genomics")

### Multi-Agent Team Examples

**Sequential Team:**
```python
from bioagent.agents import SequentialTeam

agent1 = Agent(config=config)
agent2 = Agent(config=config)

team = SequentialTeam([agent1, agent2], connect_prompt="Continue:")
result = await team.execute("Analyze this dataset")
```

**Hierarchical Team:**
```python
from bioagent.agents import HierarchicalTeam

supervisor = Agent(config=config)
genetics_agent = Agent(config=config)
genomics_agent = Agent(config=config)

team = HierarchicalTeam(supervisor, [genetics_agent, genomics_agent])
result = await team.execute("Analyze gene expression data")
```

### Domain-Based Tool Management

Agent methods for tool domain management:
- `enable_tool_domain(domain)` - Enable all tools in a domain
- `disable_tool_domain(domain)` - Disable all tools in a domain
- `list_tool_domains()` - List all available domains
- `register_tool(tool_func)` - Register custom tools

Example:
```python
# Disable genetics tools during execution
agent.disable_tool_domain("genetics")

# Enable genomics tools
agent.enable_tool_domain("genomics")

# List available domains
domains = agent.list_tool_domains()
print(domains)  # ['database', 'analysis', 'files', 'genomics', ...]
```

## Environment Variables

Required for operation:
- `ANTHROPIC_API_KEY` - For Claude models (or `ZHIPU_API_KEY` for GLM)
- `BIOAGENT_MODEL` - Model name (default: `claude-sonnet-4-20250514`)

Optional:
- `BIOAGENT_BASE_URL` - Custom API endpoint (e.g., Zhipu: `https://open.bigmodel.cn/api/coding/paas/v4`)
- `BIOAGENT_LOGS_PATH` - Path for log files (default: `./bioagent_logs`)
- `BIOAGENT_LOG_LEVEL` - Logging level (default: `INFO`)
- `BIOAGENT_MAX_TOOL_ITERATIONS` - Max tool loops (default: `10`)

Phase 2 - Biomni Integration:
- `BIOAGENT_ENABLE_BIOMNI` - Enable Biomni tools (default: false)
- `BIOAGENT_BIOMNI_PATH` - Path to Biomni installation
- `BIOAGENT_BIOMNI_DOMAINS` - Comma-separated domains to load (e.g., "genetics,genomics")

Phase 2 - Multi-Agent:
- `BIOAGENT_ENABLE_MULTI_AGENT` - Enable multi-agent mode (default: false)
- `BIOAGENT_AGENT_TEAM_MODE` - Team mode: "single", "sequential", "hierarchical", "swarm", "agent_as_tool"

## LLM Provider Selection

The framework automatically selects the LLM provider:
1. If `BIOAGENT_BASE_URL` is set → uses `OpenAIProvider` (for custom endpoints)
2. If model name contains "claude" or "anthropic" → uses `AnthropicProvider`
3. If model name contains "gpt", "openai", or "glm" → uses `OpenAIProvider`

This allows using OpenAI-compatible APIs (like Zhipu GLM) by setting the base_url.

## Testing

The test suite (`scripts/test_bioagent.py`) covers:
- `@tool` decorator functionality
- ToolRegistry operations
- ToolLoader scanning
- Observability (logger, metrics, cost tracking)
- Configuration loading
- Core tool execution

Phase 2 tests (`tests/test_phase2.py`) cover:
- ToolAdapter functionality
- BiomniToolAdapter integration
- Domain enable/disable
- SequentialTeam execution
- Configuration loading with new options

Run tests before committing changes.
