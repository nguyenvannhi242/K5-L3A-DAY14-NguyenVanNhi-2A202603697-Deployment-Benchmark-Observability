"""Giới hạn request theo API key trên cửa sổ trượt 60 giây."""

from hashlib import sha256
from uuid import uuid4

from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

WINDOW_MS = 60_000

# Redis chạy toàn bộ phép kiểm và cập nhật trong một lần để các worker
# không thể cùng thấy một lượt trống rồi cùng sử dụng nó.
reserve_request = r.register_script(
    """
    local key = KEYS[1]
    local limit = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local time = redis.call('TIME')
    local now = tonumber(time[1]) * 1000 + math.floor(tonumber(time[2]) / 1000)

    redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
    if redis.call('ZCARD', key) >= limit then
        local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
        return math.max(1, math.ceil((tonumber(oldest[2]) + window - now) / 1000))
    end

    redis.call('ZADD', key, now, ARGV[3])
    redis.call('PEXPIRE', key, window)
    return 0
    """
)


def check_rate_limit(key: str) -> None:
    key_hash = sha256(key.encode()).hexdigest()
    retry_after = reserve_request(
        keys=[f"agent:rate_limit:{key_hash}"],
        args=[settings.rate_limit_per_minute, WINDOW_MS, uuid4().hex],
    )
    if retry_after:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
