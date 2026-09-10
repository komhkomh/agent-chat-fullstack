"""Redis 连接池单例（第23课生产实践：全局一个池，到处 import）"""
import os

import redis

pool = redis.Redis(
    host=os.getenv("REDIS_HOST", "127.0.0.1"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True,
    socket_timeout=5,
)


def allow_request(user_id: str, limit: int = 20, window: int = 60) -> bool:
    """固定窗口限流（第23课练习的生产版）：每分钟 limit 次"""
    import time
    key = f"rate_limit:{user_id}:{int(time.time() // window)}"
    count = pool.incr(key)
    if count == 1:
        pool.expire(key, window)
    return count <= limit
