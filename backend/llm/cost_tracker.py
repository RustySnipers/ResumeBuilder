"""
Cost Tracker - Phase 3.1

Tracks LLM API usage and costs for budget management.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RequestRecord:
    """Record of a single API request."""

    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cost: float


class CostTracker:
    """
    Tracks LLM API usage and costs.

    Maintains statistics for:
    - Total requests
    - Token usage (input/output)
    - Cost accumulation
    - Per-model breakdown
    """

    def __init__(self):
        """Initialize cost tracker."""
        self.requests: List[RequestRecord] = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.requests_by_model: Dict[str, int] = {}
        self.cost_by_model: Dict[str, float] = {}

    def track_request(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ) -> None:
        """
        Track a single API request.

        Args:
            model: Model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost: Cost in USD
        """
        record = RequestRecord(
            timestamp=datetime.utcnow(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )

        self.requests.append(record)
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost

        # Track by model
        self.requests_by_model[model] = self.requests_by_model.get(model, 0) + 1
        self.cost_by_model[model] = self.cost_by_model.get(model, 0.0) + cost

        logger.debug(
            f"Tracked request: {model} - {input_tokens}+{output_tokens} tokens, "
            f"${cost:.4f}"
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics.

        Returns:
            Dictionary with statistics:
                - total_requests: Total number of requests
                - total_input_tokens: Total input tokens
                - total_output_tokens: Total output tokens
                - total_tokens: Total tokens (input + output)
                - total_cost: Total cost in USD
                - requests_by_model: Breakdown by model
                - cost_by_model: Cost breakdown by model
                - average_cost_per_request: Average cost
        """
        total_requests = len(self.requests)

        return {
            "total_requests": total_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost": self.total_cost,
            "requests_by_model": dict(self.requests_by_model),
            "cost_by_model": dict(self.cost_by_model),
            "average_cost_per_request": (
                self.total_cost / total_requests if total_requests > 0 else 0.0
            ),
        }

    def get_recent_requests(self, limit: int = 10) -> List[RequestRecord]:
        """
        Get most recent requests.

        Args:
            limit: Maximum number of requests to return

        Returns:
            List of recent RequestRecord objects
        """
        return self.requests[-limit:]

    def reset(self) -> None:
        """Reset all statistics."""
        self.requests.clear()
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.requests_by_model.clear()
        self.cost_by_model.clear()

        logger.info("Cost tracker statistics reset")

    def export_stats(self) -> Dict[str, Any]:
        """
        Export detailed statistics for reporting.

        Returns:
            Comprehensive statistics dictionary
        """
        stats = self.get_stats()

        # Add detailed request history
        stats["request_history"] = [
            {
                "timestamp": r.timestamp.isoformat(),
                "model": r.model,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cost": r.cost,
            }
            for r in self.requests
        ]

        return stats
