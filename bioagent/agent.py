"""
Main Agent class for BioAgent.

Implements the core agent execution loop with tool calling.
"""

import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from bioagent.agents.factory import SimpleAgentFactory

from bioagent.config import BioAgentConfig
from bioagent.state import AgentState, AgentStatus, ToolResult, LLMCall, Message
from bioagent.llm import get_llm_provider, Message as LLMMessage, LLMResponse
from bioagent.tools.registry import ToolRegistry
from bioagent.tools.loader import ToolLoader
from bioagent.tools.adapter import ToolAdapter, BiomniToolAdapter
from bioagent.tools.base import ToolInfo
from bioagent.observability import Logger, Metrics, CostTracker
from bioagent.tasks.manager import TaskManager
from bioagent.tasks.todo import TodoWrite
from bioagent.background.manager import BackgroundTaskManager
from bioagent.worktree.manager import WorktreeManager, EventBus
from bioagent.worktree.coordinator import WorktreeCoordinator


class Agent:
    """
    Main BioAgent class.

    Implements a ReAct-style agent with tool calling capabilities.
    """

    def __init__(
        self,
        config: Optional[BioAgentConfig] = None,
        system_prompt: Optional[str] = None
    ):
        """
        Initialize the agent.

        Args:
            config: Configuration for the agent (uses defaults if not provided)
            system_prompt: Optional custom system prompt
        """
        # Configuration
        self.config = config or BioAgentConfig.from_env()
        self.config.validate()

        # Observability
        self.logger = Logger("bioagent", self.config)
        self.metrics = Metrics() if self.config.enable_metrics else None
        self.cost_tracker = CostTracker() if self.config.enable_cost_tracking else None

        # State
        self.session_id = str(uuid.uuid4())[:8]
        self.state = AgentState()
        self.state.metadata["session_id"] = self.session_id

        # System prompt
        if system_prompt is None:
            from bioagent.prompts import SYSTEM_PROMPT
            self.system_prompt = SYSTEM_PROMPT
        else:
            self.system_prompt = system_prompt

        # Tool system
        self.tool_registry = ToolRegistry()
        self.loader = ToolLoader(self.tool_registry)
        self.tool_adapter: Optional[ToolAdapter] = None
        self._load_tools()

        # Task system
        self.task_manager: Optional[TaskManager] = None
        self.todo: Optional[TodoWrite] = None
        if self.config.enable_task_tracking:
            self._load_task_system()

        # Background task system
        self.bg_manager: Optional[BackgroundTaskManager] = None
        if self.config.enable_background_tasks:
            self._load_background_system()

        # Simple multi-agent factory
        self.agent_factory: Optional["SimpleAgentFactory"] = None
        if self.config.enable_multi_agent:
            # Import here to avoid circular import
            from bioagent.agents.factory import SimpleAgentFactory
            self.agent_factory = SimpleAgentFactory(self.config, self.logger)

        # Context management system
        self.context_manager = None
        if self.config.enable_context_compression:
            self._load_context_system()

        # Worktree system
        self.worktree_manager: Optional[WorktreeManager] = None
        self.worktree_coordinator: Optional[WorktreeCoordinator] = None
        if self.config.enable_worktree:
            self._load_worktree_system()

        # LLM Provider
        self.llm = get_llm_provider(self.config)

        # Set LLM provider for context manager (needed for summarization)
        if self.context_manager:
            self.context_manager.set_llm_provider(self.llm)

        self.logger.info(
            f"Agent initialized",
            session_id=self.session_id,
            model=self.config.model,
            tools=len(self.tool_registry)
        )

    def _load_tools(self) -> None:
        """Load all available tools."""
        # Load core tools from package
        try:
            self.tool_registry.register_from_package("bioagent.tools.core")
            self.logger.debug(
                f"Loaded core tools: {self.tool_registry.list_tool_names()}"
            )
        except Exception as e:
            self.logger.warning(f"Failed to load core tools: {e}")

        # Load external tools from Biomni if enabled
        if self.config.enable_biomni_tools:
            self._load_biomni_tools()

    def _load_biomni_tools(self) -> None:
        """Load Biomni tools via adapter."""
        try:
            self.tool_adapter = BiomniToolAdapter(
                registry=self.tool_registry,
                logger=self.logger,
                biomni_path=self.config.biomni_path
            )

            count = self.tool_adapter.register_all(
                domains=self.config.biomni_domains
            )

            self.logger.info(
                f"Loaded {count} Biomni tools from "
                f"{len(self.tool_adapter.list_available_domains())} domains"
            )

            # Log available domains
            domains = self.tool_adapter.list_available_domains()
            self.logger.debug(f"Available domains: {domains}")

        except Exception as e:
            self.logger.warning(f"Failed to load Biomni tools: {e}")
            self.tool_adapter = None

    def _load_task_system(self) -> None:
        """Initialize the task system if enabled."""
        try:
            # Create tasks directory if it doesn't exist
            self.config.tasks_dir.mkdir(parents=True, exist_ok=True)

            # Initialize TaskManager
            self.task_manager = TaskManager(self.config.tasks_dir, self.logger)

            # Initialize TodoWrite
            self.todo = TodoWrite(self.task_manager, self.logger)

            # Register task tools
            self._register_task_tools()

            self.logger.info(
                f"Task system initialized with {self.config.tasks_dir}",
                tasks_dir=str(self.config.tasks_dir)
            )

        except Exception as e:
            self.logger.warning(f"Failed to initialize task system: {e}")
            self.task_manager = None
            self.todo = None

    def _register_task_tools(self) -> None:
        """Register task management tools."""
        from bioagent.tools.base import tool

        @tool(domain="tasks")
        async def create_task(subject: str, description: str,
                             active_form: str = "", priority: str = "medium",
                             persist: bool = True) -> Dict[str, Any]:
            """
            Create a new task for tracking work.

            Use this tool when you need to plan or track multiple steps of work.

            Args:
                subject: Brief title of the task (max 100 chars)
                description: Detailed description of what needs to be done
                active_form: Present continuous form for display (e.g., "Analyzing data")
                priority: Priority level (low, medium, high, critical)
                persist: Whether to persist the task to disk

            Returns:
                Dictionary with task ID and details
            """
            if self.todo is None:
                return {"error": "Task system is not enabled"}
            return self.todo.create(subject, description, active_form, priority, persist)

        @tool(domain="tasks")
        async def update_task(task_id: str, status: Optional[str] = None,
                             priority: Optional[str] = None) -> Dict[str, Any]:
            """
            Update an existing task's status or priority.

            Use this tool to mark tasks as completed or change their priority.

            Args:
                task_id: Unique identifier of the task to update
                status: New status (pending, in_progress, completed, failed)
                priority: New priority (low, medium, high, critical)

            Returns:
                Updated task dictionary
            """
            if self.todo is None:
                return {"error": "Task system is not enabled"}
            return self.todo.update(task_id, status, priority)

        @tool(domain="tasks")
        async def list_tasks(status: Optional[str] = None,
                            priority: Optional[str] = None) -> List[Dict[str, Any]]:
            """
            List all tasks with optional filtering.

            Use this tool to see what tasks are currently tracked.

            Args:
                status: Filter by status (pending, in_progress, completed, failed)
                priority: Filter by priority (low, medium, high, critical)

            Returns:
                List of task dictionaries
            """
            if self.todo is None:
                return []
            return self.todo.list_all(status, priority)

        @tool(domain="tasks")
        async def get_task(task_id: str) -> Dict[str, Any]:
            """
            Get detailed information about a specific task.

            Use this tool to get full details including dependencies.

            Args:
                task_id: Unique identifier of the task

            Returns:
                Task dictionary with all details
            """
            if self.todo is None:
                return {"error": "Task system is not enabled"}
            result = self.todo.get(task_id)
            return result or {"error": f"Task {task_id} not found"}

        # Register the task tools
        self.tool_registry.register(create_task)
        self.tool_registry.register(update_task)
        self.tool_registry.register(list_tasks)
        self.tool_registry.register(get_task)

        self.logger.debug("Registered task management tools")

    def _load_background_system(self) -> None:
        """Initialize background task system if enabled."""
        try:
            # Initialize BackgroundTaskManager
            self.bg_manager = BackgroundTaskManager(
                max_retained=self.config.max_background_tasks,
                logger=self.logger,
            )

            # Register background tools
            self._register_background_tools()

            self.logger.info(
                "Background task system initialized",
                max_retained=self.config.max_background_tasks,
            )

        except Exception as e:
            self.logger.warning(f"Failed to initialize background system: {e}")
            self.bg_manager = None

    def _register_background_tools(self) -> None:
        """Register background task management tools."""
        from bioagent.tools.base import tool
        from bioagent.tools.core.background import (
            run_background,
            check_background,
            cancel_background,
        )

        # Register run_background tool (manual registration to inject context)
        @tool(domain="background")
        async def bg_run_background(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
            """
            Run a tool in the background without blocking.

            Use this for long-running operations that should not block the agent.

            Args:
                tool_name: Name of the tool to run in background
                tool_args: Arguments to pass to the tool (as a dictionary)

            Returns:
                Dictionary with task_id and status information
            """
            return run_background(tool_name, tool_args, self)

        # Register check_background tool
        @tool(domain="background")
        async def bg_check_background(task_id: Optional[str] = None) -> Dict[str, Any]:
            """
            Check the status of background tasks.

            Args:
                task_id: Optional task ID to check. If None, returns all tasks.

            Returns:
                Dictionary with task status information or list of all tasks
            """
            return check_background(task_id, self)

        # Register cancel_background tool
        @tool(domain="background")
        async def bg_cancel_background(task_id: str) -> Dict[str, Any]:
            """
            Cancel a running background task.

            Args:
                task_id: ID of the task to cancel

            Returns:
                Dictionary with cancellation status
            """
            return cancel_background(task_id, self)

        # Register the background tools
        self.tool_registry.register(bg_run_background)
        self.tool_registry.register(bg_check_background)
        self.tool_registry.register(bg_cancel_background)

        self.logger.debug("Registered background task management tools")

    def _load_context_system(self) -> None:
        """Initialize context manager if enabled."""
        try:
            from bioagent.context import ContextManager

            self.context_manager = ContextManager(self.config, self.logger)
            self.logger.info(
                "Context management initialized",
                max_tokens=self.config.context_max_tokens,
                keep_recent=self.config.context_keep_recent,
                transcripts_dir=str(self.config.transcripts_dir)
            )
        except Exception as e:
            self.logger.warning(f"Failed to initialize context system: {e}")
            self.context_manager = None

    def _load_worktree_system(self) -> None:
        """Initialize worktree system if enabled."""
        try:
            # Detect repo root
            repo_root = self._detect_repo_root()

            # Initialize WorktreeManager
            self.worktree_manager = WorktreeManager(
                repo_root=repo_root,
                tasks_dir=self.config.tasks_dir,
                worktrees_dir=self.config.worktrees_dir,
                logger=self.logger
            )

            # Initialize WorktreeCoordinator
            self.worktree_coordinator = WorktreeCoordinator(
                self.worktree_manager,
                self.logger
            )

            # Register worktree tools
            self._register_worktree_tools()

            self.logger.info(
                "Worktree system initialized",
                repo_root=str(repo_root),
                worktrees_dir=str(self.config.worktrees_dir)
            )
        except Exception as e:
            self.logger.warning(f"Failed to initialize worktree system: {e}")
            self.worktree_manager = None
            self.worktree_coordinator = None

    def _detect_repo_root(self) -> Path:
        """
        Detect git repository root.

        Returns:
            Path to repo root or current directory if not in git repo
        """
        try:
            import subprocess
            r = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=10
            )
            if r.returncode == 0:
                root = Path(r.stdout.strip())
                return root if root.exists() else Path.cwd()
        except Exception:
            pass
        return Path.cwd()

    def _register_worktree_tools(self) -> None:
        """Register worktree management tools."""
        from bioagent.tools.base import tool

        # Register worktree_create tool
        @tool(domain="worktree")
        async def wt_create(
            name: str,
            task_id: Optional[str] = None,
            base_ref: str = "HEAD"
        ) -> Dict[str, Any]:
            """
            Create a new git worktree and optionally bind it to a task.

            Worktrees provide isolated directories for parallel task execution.
            Use worktrees when working on multiple tasks simultaneously to avoid conflicts.

            Args:
                name: Worktree name (1-40 chars: letters, numbers, ., _, -)
                task_id: Optional task ID to bind the worktree to
                base_ref: Git reference to create worktree from (default: HEAD)

            Returns:
                Dictionary with worktree information
            """
            if self.worktree_manager is None:
                return {"error": "Worktree system is not enabled"}
            return self.worktree_manager.create(name, task_id, base_ref)

        # Register worktree_list tool
        @tool(domain="worktree")
        async def wt_list() -> Dict[str, Any]:
            """
            List all worktrees tracked in the index.

            Use this to see what worktrees exist and their status.

            Returns:
                Dictionary with list of worktrees and their details
            """
            if self.worktree_manager is None:
                return {"error": "Worktree system is not enabled"}
            return {"worktrees": self.worktree_manager.list_all()}

        # Register worktree_get tool
        @tool(domain="worktree")
        async def wt_get(name: str) -> Dict[str, Any]:
            """
            Get detailed information about a specific worktree.

            Args:
                name: Worktree name

            Returns:
                Worktree dictionary with full details or error if not found
            """
            if self.worktree_manager is None:
                return {"error": "Worktree system is not enabled"}
            result = self.worktree_manager.get(name)
            return result or {"error": f"Worktree '{name}' not found"}

        # Register worktree_status tool
        @tool(domain="worktree")
        async def wt_status(name: str) -> str:
            """
            Show git status for a worktree.

            Use this to check what changes exist in a worktree.

            Args:
                name: Worktree name

            Returns:
                Git status output showing modified/added/deleted files
            """
            if self.worktree_manager is None:
                return "Error: Worktree system is not enabled"
            return self.worktree_manager.status(name)

        # Register worktree_run tool
        @tool(domain="worktree")
        async def wt_run(
            name: str,
            command: str,
            timeout: int = 300
        ) -> str:
            """
            Run a shell command in a worktree directory.

            Use this to execute commands within an isolated worktree context.

            Args:
                name: Worktree name to run command in
                command: Shell command to execute
                timeout: Command timeout in seconds (default: 300)

            Returns:
                Command output (stdout + stderr), or error message
            """
            if self.worktree_manager is None:
                return "Error: Worktree system is not enabled"
            return self.worktree_manager.run(name, command, timeout)

        # Register worktree_remove tool
        @tool(domain="worktree")
        async def wt_remove(
            name: str,
            force: bool = False,
            complete_task: bool = False
        ) -> str:
            """
            Remove a worktree and optionally complete its bound task.

            Use this to clean up a worktree after work is done.
            Setting complete_task=True will also mark the bound task as completed.

            Args:
                name: Worktree name to remove
                force: Force removal even if worktree has uncommitted changes
                complete_task: If True, mark the bound task as completed

            Returns:
                Status message confirming removal
            """
            if self.worktree_manager is None:
                return "Error: Worktree system is not enabled"
            try:
                return self.worktree_manager.remove(name, force, complete_task)
            except Exception as e:
                return f"Error: {e}"

        # Register worktree_keep tool
        @tool(domain="worktree")
        async def wt_keep(name: str) -> Dict[str, Any]:
            """
            Mark a worktree as kept without removing it.

            Use this to preserve a worktree for later use (e.g., for code review).

            Args:
                name: Worktree name to keep

            Returns:
                Updated worktree dictionary with status="kept"
            """
            if self.worktree_manager is None:
                return {"error": "Worktree system is not enabled"}
            try:
                return self.worktree_manager.keep(name)
            except Exception as e:
                return {"error": str(e)}

        # Register worktree_events tool
        @tool(domain="worktree")
        async def wt_events(limit: int = 20) -> str:
            """
            List recent worktree lifecycle events.

            Use this to see the history of worktree and task operations.

            Args:
                limit: Maximum number of events to return (default: 20)

            Returns:
                JSON string of recent events
            """
            if self.worktree_manager is None:
                return "[]"
            return self.worktree_manager.list_events(limit)

        # Register worktree_summary tool
        @tool(domain="worktree")
        async def wt_summary() -> Dict[str, Any]:
            """
            Get a summary of all worktrees.

            Use this to quickly see worktree statistics.

            Returns:
                Dictionary with worktree counts by status
            """
            if self.worktree_manager is None:
                return {"error": "Worktree system is not enabled"}
            return self.worktree_manager.get_summary()

        # Register worktree tools
        self.tool_registry.register(wt_create)
        self.tool_registry.register(wt_list)
        self.tool_registry.register(wt_get)
        self.tool_registry.register(wt_status)
        self.tool_registry.register(wt_run)
        self.tool_registry.register(wt_remove)
        self.tool_registry.register(wt_keep)
        self.tool_registry.register(wt_events)
        self.tool_registry.register(wt_summary)

        self.logger.debug("Registered worktree management tools")

    def register_tool(self, tool_func) -> None:
        """
        Register a custom tool to the registry.

        Args:
            tool_func: A function decorated with @tool
        """
        self.tool_registry.register(tool_func)
        self.logger.debug(f"Registered custom tool: {tool_func.__name__}")

    def enable_tool_domain(self, domain: str) -> int:
        """
        Enable all tools in a domain.

        Args:
            domain: Domain name to enable

        Returns:
            Number of tools enabled
        """
        count = 0

        # Enable in core registry
        registry_count = self.tool_registry.enable_domain(domain)
        count += registry_count

        # Enable in external adapter if available
        if self.tool_adapter:
            adapter_count = self.tool_adapter.enable_domain(domain)
            count += adapter_count

        if count > 0:
            self.logger.info(f"Enabled {count} tools in domain '{domain}'")

        return count

    def disable_tool_domain(self, domain: str) -> int:
        """
        Disable all tools in a domain.

        Args:
            domain: Domain name to disable

        Returns:
            Number of tools disabled
        """
        count = 0

        # Disable in core registry
        registry_count = self.tool_registry.disable_domain(domain)
        count += registry_count

        # Disable in external adapter if available
        if self.tool_adapter:
            adapter_count = self.tool_adapter.disable_domain(domain)
            count += adapter_count

        if count > 0:
            self.logger.info(f"Disabled {count} tools in domain '{domain}'")

        return count

    def list_tool_domains(self) -> List[str]:
        """
        List all available tool domains.

        Returns:
            List of domain names
        """
        if self.tool_adapter:
            return self.tool_adapter.list_available_domains()
        return []

    def get_enabled_tools(self, domain: Optional[str] = None) -> List[ToolInfo]:
        """
        Get list of enabled tools.

        Args:
            domain: Optional filter by domain

        Returns:
            List of enabled ToolInfo objects
        """
        # Get tools from core registry
        tools = self.tool_registry.get_enabled_tools(domain=domain)

        # Add tools from external adapter if available
        if self.tool_adapter:
            adapter_tools = self.tool_adapter.get_enabled_tools(domain=domain)
            # Combine and deduplicate (by tool name)
            tool_names = {t.name for t in tools}
            for tool in adapter_tools:
                if tool.name not in tool_names:
                    tools.append(tool)
                    tool_names.add(tool.name)

        return tools

    async def execute(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute a query through the agent.

        Args:
            query: The user query to process
            context: Optional context variables

        Returns:
            The agent's response to the query
        """
        self.state.status = AgentStatus.THINKING
        self.state.context_variables.update(context or {})

        # Add user message to history
        self.state.add_message("user", query)

        self.logger.log_state_transition("idle", "thinking", session_id=self.session_id)

        # Check for multi-agent delegation based on task complexity
        if self.agent_factory and self.agent_factory.should_delegate(query):
            if self.config.log_delegation_decision:
                self.logger.info(
                    f"Task complexity warrants multi-agent delegation",
                    session_id=self.session_id,
                    query=query
                )
            # Create and execute multi-agent team
            team = self.agent_factory.create_multi_agent_team()
            result = await team.execute(query, context=context)
            self.state.status = AgentStatus.COMPLETED
            return result

        # Apply smart domain filtering based on query
        self._smart_domain_filter(query)

        # Build messages for LLM
        messages = self._build_messages(query)

        # Drain background task notifications and inject as user messages
        if self.bg_manager:
            notifications = self.bg_manager.drain_notifications()
            if notifications:
                notif_text = "\n".join(
                    f"[bg:{n.task_id}] {n.status.value}: {chr(10).join(n.output_lines[-5:])}"
                    if n.output_lines
                    else f"[bg:{n.task_id}] {n.status.value}"
                    for n in notifications
                )
                messages.append(
                    LLMMessage(
                        role="user",
                        content=f"<background-results>\n{notif_text}\n</background-results>",
                    )
                )
                self.logger.info(
                    f"Injected {len(notifications)} background task notification(s)",
                    session_id=self.session_id,
                )

        # Apply micro_compact before LLM call (Layer 1)
        if self.context_manager:
            messages = self.context_manager.micro_compact(messages)

        iteration = 0
        max_iterations = self.config.max_tool_iterations

        while iteration < max_iterations:
            iteration += 1

            # Check for convergence or diminishing returns
            if self._check_convergence() or self._has_diminishing_returns():
                self.logger.info(
                    "Stopping early due to convergence or diminishing returns",
                    session_id=self.session_id,
                    iteration=iteration
                )
                # Generate final response from accumulated tool results
                final_response = await self._generate_final_response()
                self.state.status = AgentStatus.COMPLETED
                return final_response

            # Check for early exit condition
            if self._should_early_exit(iteration):
                self.logger.info(
                    "Early exit condition met",
                    session_id=self.session_id,
                    iteration=iteration
                )
                # Generate final response from accumulated tool results
                final_response = await self._generate_final_response()
                self.state.status = AgentStatus.COMPLETED
                return final_response

            # Call LLM
            self.state.status = AgentStatus.THINKING
            tools_def = self.tool_registry.to_openai_format()

            try:
                response = await self.llm.call(
                    messages=messages,
                    tools=tools_def
                )
            except Exception as e:
                self.logger.error(f"LLM call failed: {e}", session_id=self.session_id)
                return f"Error: Failed to process query - {str(e)}"

            # Record metrics
            if self.metrics:
                self.metrics.record_llm_call(
                    model=response.model or self.config.model,
                    tokens=response.total_tokens,
                    duration=response.duration_ms
                )
            if self.cost_tracker:
                self.cost_tracker.record(
                    model=response.model or self.config.model,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens
                )

            # Add assistant response to history
            if response.content:
                self.state.add_message("assistant", response.content)

            # Log the call
            self.logger.log_llm_call(
                model=response.model or self.config.model,
                tokens={
                    "input": response.input_tokens,
                    "output": response.output_tokens,
                    "total": response.total_tokens
                },
                cost=response.cost,
                duration=response.duration_ms,
                session_id=self.session_id
            )

            # Record LLM call in state
            llm_call = LLMCall(
                model=response.model or self.config.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                total_tokens=response.total_tokens,
                cost=response.cost,
                duration_ms=response.duration_ms,
                tool_calls=[tc.name for tc in (response.tool_calls or [])]
            )
            self.state.add_llm_call(llm_call)

            # Check if tools were requested
            if not response.tool_calls:
                # No tools, return the content
                self.state.status = AgentStatus.COMPLETED
                return response.content or "No response generated."

            # Execute tools
            self.state.status = AgentStatus.EXECUTING_TOOL

            for tool_call in response.tool_calls:
                # Handle compact tool specially (Layer 3 - manual compact)
                if tool_call.name == "compact":
                    focus = tool_call.arguments.get("focus", "")
                    self.logger.info(
                        "Manual compact tool triggered",
                        focus=focus,
                        session_id=self.session_id
                    )
                    if self.context_manager:
                        messages = await self.context_manager.manual_compress(messages, focus)
                    # Add acknowledgment message
                    messages.append(LLMMessage(
                        role="tool",
                        content="Context compressed successfully.",
                        tool_call_id=tool_call.id
                    ))
                    continue

                # Check for redundant tool calls
                # Check for redundant tool calls
                if self._is_redundant_call(tool_call.name, tool_call.arguments):
                    self.logger.warning(
                        f"Skipping redundant tool call: {tool_call.name}",
                        session_id=self.session_id
                    )
                    continue

                # Add tool call to messages
                messages.append(LLMMessage(
                    role="user",
                    content=f"Executing {tool_call.name}",
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    tool_args=tool_call.arguments
                ))

                # Execute the tool
                start_time = time.time()
                try:
                    result = await self.tool_registry.execute(
                        tool_call.name,
                        tool_call.arguments
                    )
                    success = True
                    error = None
                except Exception as e:
                    result = {"error": str(e)}
                    success = False
                    error = str(e)

                duration = (time.time() - start_time) * 1000

                # Record tool result
                tool_result = ToolResult(
                    tool_name=tool_call.name,
                    success=success,
                    result=result,
                    error=error,
                    duration_ms=duration,
                    tool_args=tool_call.arguments
                )
                self.state.add_tool_result(tool_result)

                # Log tool call
                if self.metrics:
                    self.metrics.record_tool_call(
                        tool=tool_call.name,
                        duration=duration,
                        success=success
                    )
                if self.cost_tracker:
                    pass  # Tools don't have direct cost in Phase 1

                self.logger.log_tool_call(
                    tool_name=tool_call.name,
                    args=tool_call.arguments,
                    success=success,
                    duration=duration,
                    error=error,
                    session_id=self.session_id
                )

                # Add tool result to messages
                result_str = str(result)
                if isinstance(result, dict) and "error" in result:
                    result_str = f"Error: {result['error']}"

                messages.append(LLMMessage(
                    role="tool",
                    content=result_str,
                    tool_call_id=tool_call.id
                ))

            # Check if auto_compact needed after each tool execution (Layer 2)
            if self.context_manager and self.context_manager.should_compress(messages):
                self.logger.info(
                    "Auto compression triggered",
                    session_id=self.session_id
                )
                messages = await self.context_manager.auto_compress(messages)

        # Max iterations reached
        return "I reached the maximum number of tool iterations. Please provide more specific instructions."

    def _build_messages(self, query: str) -> List[LLMMessage]:
        """Build the initial message list for LLM call."""
        messages = [
            LLMMessage(role="system", content=self.system_prompt),
        ]

        # Add recent conversation history
        recent_messages = self.state.messages[-(self.config.max_message_history-1):]
        for msg in recent_messages:
            messages.append(LLMMessage(
                role=msg.role,
                content=msg.content
            ))

        return messages

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session."""
        return {
            "session_id": self.session_id,
            "state": {
                "status": self.state.status.value,
                "message_count": len(self.state.messages),
                "tool_calls": len(self.state.tool_results),
                "llm_calls": len(self.state.llm_calls)
            },
            "costs": self.state.get_cost_summary(),
            "metrics": self.metrics.get_summary() if self.metrics else None
        }

    def _check_convergence(self) -> bool:
        """检测工具调用是否收敛"""
        if not self.config.enable_convergence_detection:
            return False

        if len(self.state.tool_results) < self.config.convergence_min_results:
            return False

        # 检查最近N次工具调用是否重复
        recent_tools = [r.tool_name for r in self.state.tool_results[-self.config.convergence_same_tool_calls:]]
        if len(set(recent_tools)) == 1:
            self.logger.info(
                f"Convergence detected: {self.config.convergence_same_tool_calls} "
                f"consecutive calls to {recent_tools[0]}",
                session_id=self.session_id
            )
            return True

        return False

    def _has_diminishing_returns(self) -> bool:
        """检测收益递减"""
        if not self.config.enable_convergence_detection:
            return False

        if len(self.state.tool_results) < 5:
            return False

        # 检查最近结果是否包含新信息
        recent_contents = [str(r.content) for r in self.state.tool_results[-5:] if r.success]
        if len(recent_contents) == 0:
            return False

        unique_content = len(set(recent_contents))
        ratio = unique_content / len(recent_contents)

        if ratio < self.config.convergence_unique_content_ratio:
            self.logger.info(
                f"Diminishing returns detected: {ratio:.2f} unique content ratio",
                session_id=self.session_id
            )
            return True

        return False

    def _score_tool_relevance(self, query: str, tool_name: str) -> float:
        """评分工具相关性"""
        if not self.config.enable_tool_relevance_scoring:
            return 1.0  # 默认相关性

        query_lower = query.lower()
        query_keywords = query_lower.split()

        # 基于关键词匹配
        tool_descriptions = {
            "query_uniprot": ["protein", "uniprot", "structure", "function", "sequence", "annotation"],
            "query_gene": ["gene", "ontology", "function", "go", "gene", "dna", "rna"],
            "query_pubmed": ["literature", "paper", "research", "study", "publication", "article"],
            "run_python_code": ["analyze", "calculate", "process", "plot", "visualize"],
            "read_file": ["file", "data", "document", "text", "content"],
            "write_file": ["file", "save", "write", "export", "store"]
        }

        if tool_name in tool_descriptions:
            score = sum(1 for kw in query_keywords if kw in tool_descriptions[tool_name])
            return score / len(query_keywords)

        return 0.0

    def _smart_domain_filter(self, query: str) -> None:
        """根据查询智能过滤工具领域"""
        if not self.config.enable_smart_domain_filter:
            return

        query_lower = query.lower()

        # Get all available domains from the tools
        all_domains = set()
        for tool in self.tool_registry.list_tools():
            all_domains.add(tool.domain)

        # TP53 基因功能查询 - 只需要数据库工具
        if any(word in query_lower for word in ["基因", "function", "gene", "protein", "uniprot", "go"]):
            # Enable database tools
            domains_to_disable = all_domains - {"database"}
            for domain in domains_to_disable:
                try:
                    self.disable_tool_domain(domain)
                except:
                    pass  # Domain might not exist
            self.logger.info("Applied domain filter for gene/protein query", session_id=self.session_id)

        # 文献调研查询 - 需要数据库工具（PubMed）
        elif any(word in query_lower for word in ["文献", "research", "paper", "pubmed", "study"]):
            # Enable only literature/database tools
            domains_to_disable = all_domains - {"database"}
            for domain in domains_to_disable:
                try:
                    self.disable_tool_domain(domain)
                except:
                    pass  # Domain might not exist
            self.logger.info("Applied domain filter for literature query", session_id=self.session_id)

        # 数据分析查询 - 需要分析和文件工具
        elif any(word in query_lower for word in ["analyze", "data", "plot", "calculate", "process"]):
            # Enable analysis and files tools
            domains_to_disable = all_domains - {"analysis", "files"}
            for domain in domains_to_disable:
                try:
                    self.disable_tool_domain(domain)
                except:
                    pass  # Domain might not exist
            self.logger.info("Applied domain filter for analysis query", session_id=self.session_id)

    def _is_redundant_call(self, tool_name: str, tool_args: dict) -> bool:
        """检查是否为冗余调用"""
        if not self.config.enable_tool_deduplication:
            return False

        # 检查最近N次调用
        recent_calls = self.state.tool_results[-5:]
        for call in recent_calls:
            if (call.tool_name == tool_name and
                call.success and
                self._similar_arguments(call.tool_args, tool_args)):
                return True
        return False

    def _similar_arguments(self, args1: dict, args2: dict) -> bool:
        """检查参数是否相似"""
        # 简单实现：检查所有键值对是否相同
        # 可以根据实际工具参数类型进行更精细的比较
        return args1 == args2

    def _should_early_exit(self, iteration: int) -> bool:
        """检查是否应该提前退出"""
        # 检查是否满足早期退出条件
        if iteration >= self.config.max_early_exit_iterations:
            # 检查最近几次工具调用的成功率
            recent_results = self.state.tool_results[-self.config.max_early_exit_iterations:]
            if all(r.success for r in recent_results):
                return True
        return False

    async def _generate_final_response(self) -> str:
        """根据工具结果生成最终响应"""
        if not self.state.tool_results:
            return "No relevant information found."

        # 收集成功的结果
        successful_results = [r for r in self.state.tool_results if r.success]

        if not successful_results:
            return "Failed to retrieve information from tools."

        # 简单总结结果
        summary = "Based on the retrieved information:\n\n"

        for i, result in enumerate(successful_results, 1):
            result_content = str(result.result)
            if isinstance(result_content, dict):
                if result_content:
                    # 提取一些关键信息
                    if "summary" in result_content:
                        summary += f"{i}. {result_content['summary']}\n"
                    elif "protein" in result_content:
                        protein = result_content.get("protein", result_content)
                        summary += f"{i}. {protein}\n"
                    elif "gene" in result_content:
                        gene = result_content.get("gene", result_content)
                        summary += f"{i}. {gene}\n"
                    else:
                        summary += f"{i}. {result_content}\n"
                else:
                    summary += f"{i}. No additional details found.\n"
            else:
                summary += f"{i}. {result_content}\n"

        # 如果有未成功的调用，记录下来
        failed_results = [r for r in self.state.tool_results if not r.success]
        if failed_results:
            summary += "\nSome queries encountered issues:\n"
            for fail in failed_results:
                summary += f"- {fail.tool_name}: {fail.error}\n"

        return summary.strip()

    def get_tasks_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all tracked tasks.

        Returns:
            Dictionary with task statistics and enabled status
        """
        if not self.task_manager:
            return {
                "enabled": False,
                "message": "Task system is not enabled"
            }

        summary = self.task_manager.get_summary()
        summary["enabled"] = True
        summary["tasks_dir"] = str(self.config.tasks_dir)

        return summary

    def get_worktree_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all worktrees.

        Returns:
            Dictionary with worktree statistics and enabled status
        """
        if not self.worktree_manager:
            return {
                "enabled": False,
                "message": "Worktree system is not enabled"
            }

        summary = self.worktree_manager.get_summary()
        summary["enabled"] = True
        summary["worktrees_dir"] = str(self.config.worktrees_dir)
        summary["git_available"] = self.worktree_manager.git_available

        return summary

    def create_agent_task(
        self,
        subject: str,
        description: str,
        active_form: str = "",
        priority: str = "medium",
    ) -> Optional[str]:
        """
        Create a task for the agent's own tracking.

        This is a convenience method for creating tasks directly
        without going through the tool system.

        Args:
            subject: Brief title of the task
            description: Detailed description of the task
            active_form: Present continuous form for display
            priority: Priority level (low, medium, high, critical)

        Returns:
            Task ID if created, None if task system is disabled
        """
        if not self.task_manager or not self.todo:
            self.logger.warning("Cannot create task: task system is not enabled")
            return None

        result = self.todo.create(
            subject=subject,
            description=description,
            active_form=active_form,
            priority=priority,
            persist=True,
        )

        return result.get("id")

    def update_agent_task(self, task_id: str, status: Optional[str] = None,
                          priority: Optional[str] = None) -> Optional[str]:
        """
        Update an agent task.

        Args:
            task_id: Unique identifier of the task
            status: New status if provided
            priority: New priority if provided

        Returns:
            Task ID if updated, None if task system is disabled
        """
        if not self.todo:
            return None

        result = self.todo.update(task_id, status, priority)
        return task_id if result else None

    def reset(self) -> None:
        """Reset the agent state for a new session."""
        self.state = AgentState()
        self.state.metadata["session_id"] = str(uuid.uuid4())[:8]
        self.session_id = self.state.metadata["session_id"]

        if self.metrics:
            self.metrics.reset()
        if self.cost_tracker:
            self.cost_tracker.reset()

        self.logger.info("Agent state reset", session_id=self.session_id)
