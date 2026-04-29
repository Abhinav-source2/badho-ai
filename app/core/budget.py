import os
from app.core.state import get_session, increment_cost

MAX_BUDGET = float(os.getenv("MAX_BUDGET_USD", "0.10"))

# Haiku pricing per token
PRICE_INPUT  = 0.80  / 1_000_000
PRICE_OUTPUT = 4.00  / 1_000_000


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return round(
        input_tokens * PRICE_INPUT + output_tokens * PRICE_OUTPUT, 8
    )


def is_over_budget(session_id: str) -> bool:
    return get_session(session_id)["budget_used"] >= MAX_BUDGET


def record_cost(session_id: str, cost: float) -> None:
    increment_cost(session_id, cost)