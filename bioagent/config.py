"""
Configuration management for BioAgent.

Loads configuration from environment variables and provides defaults.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()


@dataclass
class BioAgentConfig:
    """Configuration for BioAgent."""

    # LLM Configuration
    model: str = "claude-sonnet-4-20250514"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120

    # Paths
    data_path: Path = field(default_factory=lambda: Path.cwd() / "bioagent_data")
    logs_path: Path = field(default_factory=lambda: Path.cwd() / "bioagent_logs")

    # Tool Configuration
    tools_dir: str = "tools"
    enable_caching: bool = True
    tools_domains_dir: Path = field(default_factory=lambda: Path.cwd() / "bioagent" / "tools" / "domains")

    # Biomni Integration
    enable_biomni_tools: bool = False
    biomni_path: Optional[str] = None
    biomni_domains: Optional[list] = None  # List of domains to load, e.g., ["genetics", "genomics"]

    # Multi-Agent Configuration
    enable_multi_agent: bool = False
    agent_team_mode: str = "single"  # "single", "sequential", "hierarchical", "swarm", "agent_as_tool"

    # Observability
    log_level: str = "INFO"
    enable_metrics: bool = True
    enable_cost_tracking: bool = True

    # Limits
    max_tool_iterations: int = 10
    max_message_history: int = 100

    @classmethod
    def from_env(cls) -> "BioAgentConfig":
        """Load configuration from environment variables."""
        config = cls()

        # LLM settings
        if api_key := os.getenv("ANTHROPIC_API_KEY"):
            config.api_key = api_key
        if model := os.getenv("BIOAGENT_MODEL"):
            config.model = model
        if base_url := os.getenv("BIOAGENT_BASE_URL"):
            config.base_url = base_url

        # Paths
        if data_path := os.getenv("BIOAGENT_DATA_PATH"):
            config.data_path = Path(data_path)
        if logs_path := os.getenv("BIOAGENT_LOGS_PATH"):
            config.logs_path = Path(logs_path)

        # Tool settings
        if tools_dir := os.getenv("BIOAGENT_TOOLS_DIR"):
            config.tools_dir = tools_dir

        # Biomni integration settings
        if enable_biomni := os.getenv("BIOAGENT_ENABLE_BIOMNI"):
            config.enable_biomni_tools = enable_biomni.lower() in ("true", "1", "yes")
        if biomni_path := os.getenv("BIOAGENT_BIOMNI_PATH"):
            config.biomni_path = biomni_path
        if biomni_domains := os.getenv("BIOAGENT_BIOMNI_DOMAINS"):
            config.biomni_domains = [d.strip() for d in biomni_domains.split(",")]

        # Multi-agent settings
        if enable_multi_agent := os.getenv("BIOAGENT_ENABLE_MULTI_AGENT"):
            config.enable_multi_agent = enable_multi_agent.lower() in ("true", "1", "yes")
        if agent_team_mode := os.getenv("BIOAGENT_AGENT_TEAM_MODE"):
            if agent_team_mode in ("single", "sequential", "hierarchical", "swarm", "agent_as_tool"):
                config.agent_team_mode = agent_team_mode

        # Observability
        if log_level := os.getenv("BIOAGENT_LOG_LEVEL"):
            config.log_level = log_level

        # Limits
        if max_iterations := os.getenv("BIOAGENT_MAX_TOOL_ITERATIONS"):
            config.max_tool_iterations = int(max_iterations)

        return config

    def validate(self) -> None:
        """Validate configuration and raise errors if invalid."""
        # Require API key for Claude models without custom base URL
        if not self.api_key and "claude" in self.model.lower() and not self.base_url:
            raise ValueError("ANTHROPIC_API_KEY is required for Claude models")
        # Require API key for custom base URL
        if not self.api_key and self.base_url:
            raise ValueError("API key is required when using custom base URL")

        self.data_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self.tools_domains_dir.mkdir(parents=True, exist_ok=True)

        # Validate multi-agent mode
        if self.agent_team_mode != "single" and not self.enable_multi_agent:
            # Auto-enable multi-agent if a team mode is specified
            self.enable_multi_agent = True


# Default configuration instance
default_config = BioAgentConfig.from_env()
