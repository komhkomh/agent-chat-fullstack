"""
第 29 课：缓存三兄弟 —— 穿透/击穿 的攻防演示
运行方式：.venv/bin/python 29_cache_problems.py（需 Redis 运行）
"""
import threading
import time

import redis

r = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)
r.flushdb()

# ---------- 模拟数据库（用计数器记录被打次数）----------
def db_query(key: str) -> str | None:
    r.incr("stat:db_hits")          # 每次查库都计数
    time.sleep(0.1)                 # 模拟 DB 耗时 100ms
    fake_db = {"user:1": "小明", "user:2": "小红"}
    return fake_db.get(key)

# ============================================================
# 一、缓存穿透：查不存在的数据
# ============================================================
print("=== ① 无防护：连查 5 次不存在的 user:999 ===")
r.set("stat:db_hits", 0)
def get_user_naive(key):
    cached = r.get(f"cache:{key}")
    if cached: return cached
    data = db_query(key)            # 缓存没有 → 查库
    if data: r.set(f"cache:{key}", data, ex=60)
    return data
for _ in range(5): get_user_naive("user:999")
print(f"   DB 被打 {r.get('stat:db_hits')} 次 💥（数据不存在，缓存永远 miss）")

print("\n=== ② 空值缓存防护 ===")
r.flushdb(); r.set("stat:db_hits", 0)
def get_user_safe(key):
    cached = r.get(f"cache:{key}")
    if cached is not None:
        return None if cached == "__NULL__" else cached
    data = db_query(key)
    if data is None:
        r.set(f"cache:{key}", "__NULL__", ex=30)   # 把"不存在"也缓存起来
        return None
    r.set(f"cache:{key}", data, ex=60)
    return data
for _ in range(5): get_user_safe("user:999")
print(f"   DB 只被打 {r.get('stat:db_hits')} 次 ✅（后续命中空值缓存）")

# ============================================================
# 二、缓存击穿：热点 key 过期瞬间，并发抢建
# ============================================================
print("\n=== ③ 无锁：热点 key 过期，5 个并发同时 miss ===")
r.flushdb(); r.set("stat:db_hits", 0)
r.set("cache:hot_item", "爆款数据", ex=1)   # 热点 key，1秒后过期
time.sleep(1.1)                              # 等它过期
def get_hot_naive():
    cached = r.get("cache:hot_item")
    if cached: return cached
    data = db_query("user:1")                # 都 miss → 都去查库
    r.set("cache:hot_item", data, ex=60)
    return data
threads = [threading.Thread(target=get_hot_naive) for _ in range(5)]
[t.start() for t in threads]; [t.join() for t in threads]
print(f"   5 个并发 → DB 被打 {r.get('stat:db_hits')} 次 💥")

print("\n=== ④ 互斥锁重建：只放行一个请求查库 ===")
r.flushdb(); r.set("stat:db_hits", 0)
def get_hot_with_lock():
    cached = r.get("cache:hot_item")
    if cached: return cached
    # 抢锁：只有一个线程能拿到
    if r.set("lock:rebuild", "1", nx=True, ex=10):
        try:
            data = db_query("user:1")        # 抢到锁的去查库
            r.set("cache:hot_item", data, ex=60)
            return data
        finally:
            r.delete("lock:rebuild")
    else:
        time.sleep(0.15)                     # 没抢到的等一下
        return r.get("cache:hot_item")       # 直接读别人重建好的缓存
threads = [threading.Thread(target=get_hot_with_lock) for _ in range(5)]
[t.start() for t in threads]; [t.join() for t in threads]
print(f"   5 个并发 → DB 只被打 {r.get('stat:db_hits')} 次 ✅")

# ============================================================
# 三、雪崩预防：TTL 抖动（一行代码的事）
# ============================================================
print("\n=== ⑤ TTL 抖动效果 ===")
import random
for i in range(5):
    ttl = 3600 + random.randint(0, 300)   # 基础1小时 + 0~5分钟抖动
    print(f"   key{i} 的 TTL: {ttl}s（过期时间自然错开，不扎堆）")

# ========== ✏️ 练习 ==========
# 1. 空值缓存引入了一个一致性问题：如果查完"不存在"之后，数据被创建了，
#    30 秒内用户一直看到"不存在"。怎么缓解？（注释写两点）
# 2. （思考）布隆过滤器的特点是"说没有就一定没有，说有可能有"。
#    为什么这个特性恰好适合防穿透？
