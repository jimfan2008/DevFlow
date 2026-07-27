import pytest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class LLMUsageRecord:
    model: str
    prompt_tokens: int
    completion_tokens: int
    timestamp: datetime
    cost: Decimal = Decimal("0")


@dataclass
class LLMBudget:
    total_budget: Decimal
    used: Decimal = Decimal("0")
    alert_threshold: Decimal = Decimal("0.8")
    period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: Optional[datetime] = None


@dataclass
class CostAlert:
    message: str
    level: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


MODEL_PRICING = {
    "gpt-4":        {"input": Decimal("0.03"),  "output": Decimal("0.06")},
    "gpt-4-turbo":  {"input": Decimal("0.01"),  "output": Decimal("0.03")},
    "gpt-3.5-turbo":{"input": Decimal("0.001"), "output": Decimal("0.002")},
    "claude-3-opus": {"input": Decimal("0.015"), "output": Decimal("0.075")},
    "claude-3-sonnet":{"input": Decimal("0.003"), "output": Decimal("0.015")},
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        raise ValueError(f"Unknown model: {model}")
    cost = (pricing["input"] * prompt_tokens + pricing["output"] * completion_tokens) / Decimal("1000")
    return cost.quantize(Decimal("0.000001"))
