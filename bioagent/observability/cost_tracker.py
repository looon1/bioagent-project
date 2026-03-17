"""
Cost tracking for BioAgent.

Tracks API costs across different models and sessions.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class CostRecord:
    """A single cost record."""
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: datetime
    operation: str = "llm_call"


class CostTracker:
    """Track costs across operations."""

    # Default pricing (can be overridden per model)
    DEFAULT_PRICING = {
        "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
        "claude-3-5-haiku-20241022": {"input": 0.0008, "output": 0.004},
    }

    def __init__(self, pricing: Optional[Dict[str, Dict[str, float]]] = None):
        """
        Initialize cost tracker.

        Args:
            pricing: Optional custom pricing dict overriding defaults
        """
        self.pricing = {**self.DEFAULT_PRICING, **(pricing or {})}
        self._records: List[CostRecord] = []
        self._session_costs: Dict[str, float] = defaultdict(float)

    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        operation: str = "llm_call",
        custom_cost: Optional[float] = None
    ) -> float:
        """
        Record a cost for an operation.

        Args:
            model: The model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            operation: Type of operation (default: "llm_call")
            custom_cost: Optional custom cost override

        Returns:
            The cost of this operation
        """
        if custom_cost is not None:
            cost = custom_cost
        else:
            pricing = self.pricing.get(model, {"input": 0.003, "output": 0.015})
            cost = (input_tokens / 1000) * pricing["input"] + \
                   (output_tokens / 1000) * pricing["output"]

        record = CostRecord(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            timestamp=datetime.now(),
            operation=operation
        )

        self._records.append(record)
        self._session_costs[model] += cost

        return cost

    def get_total_cost(self) -> float:
        """Get total cost across all operations."""
        return sum(record.cost for record in self._records)

    def get_cost_by_model(self) -> Dict[str, float]:
        """Get total cost breakdown by model."""
        return dict(self._session_costs)

    def get_cost_by_operation(self) -> Dict[str, float]:
        """Get total cost breakdown by operation type."""
        costs = defaultdict(float)
        for record in self._records:
            costs[record.operation] += record.cost
        return dict(costs)

    def get_token_summary(self) -> Dict[str, Dict[str, int]]:
        """Get token usage summary by model."""
        summary = defaultdict(lambda: {"input": 0, "output": 0, "total": 0})
        for record in self._records:
            summary[record.model]["input"] += record.input_tokens
            summary[record.model]["output"] += record.output_tokens
            summary[record.model]["total"] += (
                record.input_tokens + record.output_tokens
            )
        return {k: dict(v) for k, v in summary.items()}

    def get_records(self) -> List[CostRecord]:
        """Get all cost records."""
        return list(self._records)

    def reset(self) -> None:
        """Reset all cost tracking."""
        self._records.clear()
        self._session_costs.clear()

    def set_pricing(self, model: str, input_cost: float, output_cost: float) -> None:
        """
        Set custom pricing for a model.

        Args:
            model: Model name
            input_cost: Cost per 1000 input tokens
            output_cost: Cost per 1000 output tokens
        """
        self.pricing[model] = {"input": input_cost, "output": output_cost}
