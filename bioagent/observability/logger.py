"""
Structured logging for BioAgent.

Provides JSON-formatted logging with context information.
"""

import json
import logging
import logging.config
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context variables if present
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
        if hasattr(record, "agent_name"):
            log_data["agent_name"] = record.agent_name

        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


class Logger:
    """Structured logger for BioAgent."""

    def __init__(self, name: str = "bioagent", config=None):
        self.name = name
        self.config = config

        # Create logger
        self.logger = logging.getLogger(name)

        # Prevent duplicate handlers
        if self.logger.handlers:
            return

        # Set level
        level = getattr(logging, (config.log_level if config else "INFO"), logging.INFO)
        self.logger.setLevel(level)

        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
        self.logger.addHandler(console_handler)

        # Add file handler if configured
        if config and config.logs_path:
            config.logs_path.mkdir(parents=True, exist_ok=True)
            log_file = config.logs_path / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(JsonFormatter())
            self.logger.addHandler(file_handler)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra={"extra": kwargs})

    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra={"extra": kwargs})

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra={"extra": kwargs})

    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, extra={"extra": kwargs})

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(message, extra={"extra": kwargs})

    def log_llm_call(self, model: str, tokens: Dict[str, int], cost: float, duration: float, **kwargs):
        """Log an LLM call."""
        self.info(
            "LLM call completed",
            event_type="llm_call",
            model=model,
            input_tokens=tokens.get("input", 0),
            output_tokens=tokens.get("output", 0),
            total_tokens=tokens.get("total", 0),
            cost=cost,
            duration_ms=duration,
            **kwargs
        )

    def log_tool_call(self, tool_name: str, args: Dict, success: bool, duration: float, **kwargs):
        """Log a tool call."""
        self.info(
            f"Tool {'executed' if success else 'failed'}",
            event_type="tool_call",
            tool_name=tool_name,
            args=args,
            success=success,
            duration_ms=duration,
            **kwargs
        )

    def log_state_transition(self, from_state: str, to_state: str, **kwargs):
        """Log a state transition."""
        self.debug(
            f"State transition: {from_state} -> {to_state}",
            event_type="state_transition",
            from_state=from_state,
            to_state=to_state,
            **kwargs
        )


# Module-level logger instance
logger = Logger("bioagent")
