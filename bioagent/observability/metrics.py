"""
Metrics collection for BioAgent.

Tracks performance metrics across agent runs.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class MetricRecord:
    """A single metric record."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


class Metrics:
    """Metrics collection system."""

    def __init__(self):
        self._metrics: List[MetricRecord] = []
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._timers: Dict[str, List[float]] = defaultdict(list)

    def increment(self, name: str, value: int = 1, tags: Dict[str, str] = None) -> None:
        """Increment a counter metric."""
        self._counters[name] += value
        self._metrics.append(MetricRecord(
            name=name,
            value=self._counters[name],
            unit="count",
            timestamp=datetime.now(),
            tags=tags or {}
        ))

    def gauge(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Set a gauge metric value."""
        self._gauges[name] = value
        self._metrics.append(MetricRecord(
            name=name,
            value=value,
            unit="value",
            timestamp=datetime.now(),
            tags=tags or {}
        ))

    def timing(self, name: str, duration_ms: float, tags: Dict[str, str] = None) -> None:
        """Record a timing metric."""
        self._timers[name].append(duration_ms)
        avg = sum(self._timers[name]) / len(self._timers[name])
        self._metrics.append(MetricRecord(
            name=f"{name}.avg",
            value=avg,
            unit="ms",
            timestamp=datetime.now(),
            tags=tags or {}
        ))

    def record_llm_call(self, model: str, tokens: int, duration: float, **kwargs) -> None:
        """Record LLM call metrics."""
        self.increment("llm.calls", tags={"model": model})
        self.gauge("llm.tokens", tokens, tags={"model": model})
        self.timing("llm.duration", duration, tags={"model": model})

    def record_tool_call(self, tool: str, duration: float, success: bool, **kwargs) -> None:
        """Record tool call metrics."""
        self.increment("tool.calls", tags={"tool": tool, "status": "success" if success else "failure"})
        self.timing(f"tool.{tool}.duration", duration, tags={"status": "success" if success else "failure"})

    def get_counter(self, name: str) -> int:
        """Get current value of a counter."""
        return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float:
        """Get current value of a gauge."""
        return self._gauges.get(name, 0.0)

    def get_timings(self, name: str) -> List[float]:
        """Get all timing values for a metric."""
        return list(self._timers.get(name, []))

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "timings": {k: {"count": len(v), "avg": sum(v)/len(v) if v else 0}
                      for k, v in self._timers.items()},
            "total_records": len(self._metrics)
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self._metrics.clear()
        self._counters.clear()
        self._gauges.clear()
        self._timers.clear()
