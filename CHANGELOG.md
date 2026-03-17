# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-03-17

### Phase 2 Complete ✅
This major release completes Phase 2 of the BioAgent roadmap with comprehensive multi-agent
and external tool integration capabilities.

### Added

#### Multi-Agent Team System
- `Team` abstract base class for agent coordination
- `SequentialTeam` - Pipeline-style execution with connect prompts
- `HierarchicalTeam` - Supervisor/delegation pattern with feedback loops
- `AgentAsToolTeam` - Sub-agents as tools pattern
- `SwarmTeam` - Handoff-based pattern with dynamic agent selection
- Team-level agent lookup and listing utilities

#### External Tool Integration
- `ToolAdapter` base class for external tool library integration
- `BiomniToolAdapter` for 105+ Biomni biomedical tools
- AST-based tool description parsing (no runtime dependencies)
- Domain-based tool enable/disable
- Tool metadata preservation

#### Unified API
- Consistent agent interface across all components
- `get_enabled_tools()` method for agent
- `tools` and `domains` properties for ToolRegistry
- `list_tools_by_domain()` for domain-specific queries
- `list_agent_tools()` for AgentAsToolTeam
- Agent descriptions support for team patterns

#### Configuration
- Biomni integration configuration options
- Multi-agent mode configuration
- Domain-based tool filtering
- Environment variable support for all Phase 2 features

#### Documentation
- `PHASE2_SUMMARY.md` - Implementation details
- `PHASE2_API_UNIFICATION.md` - API consistency report
- Updated CLAUDE.md with Phase 2 guidance
- Updated README.md with Phase 2 examples

#### Testing
- `tests/test_phase2.py` - Comprehensive Phase 2 tests
- `scripts/test_phase2_fixed.py` - Unified API tests (100% pass)
- `scripts/test_phase2_questions.py` - Question-based validation
- All tests passing with 100% pass rate

### Fixed
- ToolRegistry now provides `tools` property for read-only access
- ToolRegistry now provides `domains` property for domain enumeration
- ToolRegistry added `list_tools_by_domain()` method
- Agent added `get_enabled_tools()` method
- AgentAsToolTeam now supports `agent_descriptions` parameter
- All team patterns export correctly from `bioagent.agents`

### Changed
- BioAgent version bumped to 2.0.0
- All Phase 2 features marked as complete
- API unified across all components
- Error handling improved for invalid configurations

## [0.1.0] - 2026-03-17

### Added
- Initial release of BioAgent framework
- Core Agent implementation with ReAct-style tool calling
- Tool registry with async/sync tool execution support
- 6 core biomedical tools:
  - `query_uniprot` - UniProt protein database access
  - `query_gene` - Gene Ontology API access
  - `query_pubmed` - PubMed literature search
  - `run_python_code` - Code execution for analysis
  - `read_file` - File reading
  - `write_file` - File writing
- LLM provider abstraction supporting:
  - OpenAI-compatible APIs (GLM, GPT)
  - Anthropic Claude
- Observability stack:
  - Structured JSON logging
  - Token usage and cost tracking
  - Performance metrics
- Command-line interface (`bioagent` command)
- Configuration management with environment variables
- Session state tracking

### Fixed
- Fixed async tool execution in `ToolRegistry.execute()`
- Fixed JSON argument parsing in `OpenAIProvider.call()`
- Added error logging for tool failures

### Documentation
- Project requirements and design specification
- Getting started guide
- Implementation summary
- Progress checklist

## [Unreleased]

### Planned
- Skills extension system with two-layer injection
- Multi-agent framework with team patterns
- Hot-pluggable tool interfaces with JSON descriptions
- Enhanced biomedical tools (GEO, KEGG, etc.)
- Web API for agent interaction
