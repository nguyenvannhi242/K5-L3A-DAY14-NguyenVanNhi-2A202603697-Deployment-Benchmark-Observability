"""Theo dõi chi phí mock LLM theo ngày UTC trong Redis."""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

# Đơn giá mô phỏng tính bằng USD trên 1.000 token.
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006


def _usage_key(now: datetime) -> str:
    return f"agent:cost:{now.date().isoformat()}"


def check_budget() -> None:
    spent = float(r.get(_usage_key(datetime.now(timezone.utc))) or 0)
    if spent >= settings.daily_budget_usd:
        raise HTTPException(status_code=402, detail="Daily budget exceeded")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    cost = (input_tokens * PRICE_INPUT_PER_1K + output_tokens * PRICE_OUTPUT_PER_1K) / 1000
    now = datetime.now(timezone.utc)
    key = _usage_key(now)
    next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    with r.pipeline() as transaction:
        transaction.incrbyfloat(key, cost)
        transaction.expireat(key, next_midnight)
        transaction.execute()
    return cost
