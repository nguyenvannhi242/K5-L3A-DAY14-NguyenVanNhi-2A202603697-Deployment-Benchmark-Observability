"""Kết nối Redis dùng chung trong mỗi worker."""

from redis import Redis
from redis.exceptions import RedisError

from app.config import settings

# Redis mở kết nối khi có lệnh đầu tiên.
r = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=2,
)


def redis_healthy() -> bool:
    try:
        return bool(r.ping())
    except RedisError:
        return False
