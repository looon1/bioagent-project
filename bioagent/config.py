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

    # Efficiency optimization settings
    enable_convergence_detection: bool = True
    enable_tool_relevance_scoring: bool = True
    enable_smart_domain_filter: bool = True
    enable_tool_deduplication: bool = True

    # Convergence thresholds
    convergence_same_tool_calls: int = 3  # Number of same tool calls to detect convergence
    convergence_min_results: int = 3     # Minimum results before checking convergence
    convergence_unique_content_ratio: float = 0.6  # Ratio of unique content needed (e.g., 0.6 = 60%)

    # Tool scoring settings
    min_relevance_score: float = 0.3     # Minimum relevance score to use a tool
    max_early_exit_iterations: int = 5    # Early exit for simple queries after this many iterations

    # Multi-Agent Delegation Configuration
    multi_agent_auto_delegate: bool = True      # Automatically delegate complex tasks
    auto_delegate_threshold: int = 0.5          # Complexity score threshold (0-1)
    log_delegation_decision: bool = True       # Log delegation decisions

    # Task System Configuration
    enable_task_tracking: bool = True          # Enable task tracking system
    tasks_dir: Path = field(default_factory=lambda: Path.cwd() / ".tasks")
    auto_resolve_dependencies: bool = True     # Auto-resolve dependencies when tasks complete
    task_completion_cleanup: bool = True       # Auto-delete completed tasks after retention period
    task_retention_days: int = 7               # Number of days to retain completed tasks

    # Background Tasks Configuration
    enable_background_tasks: bool = True         # Enable background task system
    max_background_tasks: int = 50            # Maximum retained completed tasks
    background_task_timeout: int = 300         # Default timeout for tool execution (seconds)

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

        # Efficiency settings
        if convergence_detection := os.getenv("BIOAGENT_ENABLE_CONVERGENCE_DETECTION"):
            config.enable_convergence_detection = convergence_detection.lower() in ("true", "1", "yes")
        if relevance_scoring := os.getenv("BIOAGENT_ENABLE_TOOL_RELEVANCE_SCORING"):
            config.enable_tool_relevance_scoring = relevance_scoring.lower() in ("true", "1", "yes")
        if smart_filter := os.getenv("BIOAGENT_ENABLE_SMART_DOMAIN_FILTER"):
            config.enable_smart_domain_filter = smart_filter.lower() in ("true", "1", "yes")
        if tool_deduplication := os.getenv("BIOAGENT_ENABLE_TOOL_DEDUPLICATION"):
            config.enable_tool_deduplication = tool_deduplication.lower() in ("true", "1", "yes")

        # Convergence thresholds
        if same_calls := os.getenv("BIOAGENT_CONVERGENCE_SAME_TOOL_CALLS"):
            config.convergence_same_tool_calls = int(same_calls)
        if min_results := os.getenv("BIOAGENT_CONVERGENCE_MIN_RESULTS"):
            config.convergence_min_results = int(min_results)
        if unique_ratio := os.getenv("BIOAGENT_CONVERGENCE_UNIQUE_CONTENT_RATIO"):
            config.convergence_unique_content_ratio = float(unique_ratio)

        # Tool scoring settings
        if min_score := os.getenv("BIOAGENT_MIN_RELEVANCE_SCORE"):
            config.min_relevance_score = float(min_score)
        if max_exit := os.getenv("BIOAGENT_MAX_EARLY_EXIT_ITERATIONS"):
            config.max_early_exit_iterations = int(max_exit)

        # Multi-agent delegation settings
        if auto_delegate := os.getenv("BIOAGENT_MULTI_AGENT_AUTO_DELEGATE"):
            config.multi_agent_auto_delegate = auto_delegate.lower() in ("true", "1", "yes")
        if threshold := os.getenv("BIOAGENT_AUTO_DELEGATE_THRESHOLD"):
            config.auto_delegate_threshold = float(threshold)
        if log_decision := os.getenv("BIOAGENT_LOG_DELEGATION_DECISION"):
            config.log_delegation_decision = log_decision.lower() in ("true", "1", "yes")

        # Task system settings
        if enable_tasks := os.getenv("BIOAGENT_ENABLE_TASK_TRACKING"):
            config.enable_task_tracking = enable_tasks.lower() in ("true", "1", "yes")
        if tasks_dir := os.getenv("BIOAGENT_TASKS_DIR"):
            config.tasks_dir = Path(tasks_dir)
        if auto_resolve := os.getenv("BIOAGENT_AUTO_RESOLVE_DEPENDENCIES"):
            config.auto_resolve_dependencies = auto_resolve.lower() in ("true", "1", "yes")
        if task_cleanup := os.getenv("BIOAGENT_TASK_COMPLETION_CLEANUP"):
            config.task_completion_cleanup = task_cleanup.lower() in ("true", "1", "yes")
        if retention_days := os.getenv("BIOAGENT_TASK_RETENTION_DAYS"):
            config.task_retention_days = int(retention_days)

        # Background task settings
        if enable_bg := os.getenv("BIOAGENT_ENABLE_BACKGROUND_TASKS"):
            config.enable_background_tasks = enable_bg.lower() in ("true", "1", "yes")
        if max_bg := os.getenv("BIOAGENT_MAX_BACKGROUND_TASKS"):
            config.max_background_tasks = int(max_bg)
        if bg_timeout := os.getenv("BIOAGENT_BACKGROUND_TASK_TIMEOUT"):
            config.background_task_timeout = int(bg_timeout)

        return config

    def validate(self) -> None:
        """Validate configuration and raise errors if invalid."""
        # Allow test mode for testing purposes
        if os.getenv("BIOAGENT_TEST_MODE"):
            return

        # Require API key for Claude models without custom base URL
        if not self.api_key and "claude" in self.model.lower() and not self.base_url:
            raise ValueError("ANTHROPIC_API_KEY is required for Claude models")
        # Require API key for custom base URL
        if not self.api_key and self.base_url:
            raise ValueError("API key is required when using custom base URL")

        self.data_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self.tools_domains_dir.mkdir(parents=True, exist_ok=True)

        # Create tasks directory if task tracking is enabled
        if self.enable_task_tracking:
            self.tasks_dir.mkdir(parents=True, exist_ok=True)

        # Validate multi-agent mode
        if self.agent_team_mode != "single" and not self.enable_multi_agent:
            # Auto-enable multi-agent if a team mode is specified
            self.enable_multi_agent = True


# Default configuration instance
default_config = BioAgentConfig.from_env()
