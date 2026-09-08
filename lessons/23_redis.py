"""
第 23 课：Redis —— 内存型键值数据库
运行方式：.venv/bin/python 23_redis.py（确保 redis-demo 容器在跑）

核心心智：Redis ≈ 一个住在内存里的、带过期时间的、超快的【大字典】
"""
import time

import redis

# 连接 Redis（对比 SQLite：那是开文件，这是连服务）
r = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)
# decode_responses=True：返回 str 而不是 bytes，省心

print("=== ① 基本操作：就是字典三件套 ===")
r.set("name", "小明")              # dict["name"] = "小明"
print(f"   GET name → {r.get('name')}")
print(f"   EXISTS name → {r.exists('name')}")
r.delete("name")
print(f"   DELETE 后再 GET → {r.get('name')}  （None = 不存在）")

print("\n=== ② TTL 过期时间（Redis 的杀手锏）===")
r.set("sms_code", "888888", ex=10)   # SET + EXpire：10秒后自动删除
print(f"   刚写入: {r.get('sms_code')}, 剩余寿命: {r.ttl('sms_code')} 秒")
time.sleep(1)
print(f"   1秒后剩余寿命: {r.ttl('sms_code')} 秒")
print("   （10秒后自动消失——不用写任何清理逻辑！）")

print("\n=== ③ 计数器 INCR（原子自增）===")
r.delete("post:1:views")
for _ in range(3):
    views = r.incr("post:1:views")   # 原子操作：并发安全，不用加锁
print(f"   帖子阅读量: {views}")

print("\n=== ④ 实战场景一：token 存储（对照15课 SQLite 版）===")
# 15课: INSERT INTO tokens ... 每次验证要 SELECT 查库
# Redis: 一行 setex，自带过期
TOKEN = "abc123token"
r.set(f"token:{TOKEN}", "xiaoming", ex=3600)   # key 带前缀是 Redis 命名惯例

# 验票（= get_current_user 的 Redis 版）
username = r.get(f"token:{TOKEN}")
print(f"   验票结果: {username}")
print(f"   这张证的剩余寿命: {r.ttl(f'token:{TOKEN}')} 秒")

print("\n=== ⑤ 实战场景二：缓存模式（Cache-Aside，先缓存后数据库）===")
# 模拟慢数据库查询
def slow_db_query(user_id: int) -> dict:
    time.sleep(0.5)   # 模拟数据库要 500ms
    return {"id": user_id, "name": "小明", "role": "dev"}

import json
def get_user_cached(user_id: int) -> tuple[dict, str]:
    key = f"cache:user:{user_id}"
    cached = r.get(key)
    if cached:
        return json.loads(cached), "🚀 缓存命中"
    data = slow_db_query(user_id)             # 缓存没有 → 查库
    r.set(key, json.dumps(data), ex=60)        # 写回缓存，60秒过期
    return data, "🐢 缓存未命中，查了数据库"

t0 = time.perf_counter(); data, src = get_user_cached(1); t1 = (time.perf_counter()-t0)*1000
print(f"   第一次调用: {src} ({t1:.0f}ms)")
t0 = time.perf_counter(); data, src = get_user_cached(1); t2 = (time.perf_counter()-t0)*1000
print(f"   第二次调用: {src} ({t2:.1f}ms)  ← 快了 {t1/max(t2,0.1):.0f} 倍")

# 清理演示数据
r.delete("sms_code", "post:1:views", f"token:{TOKEN}", "cache:user:1")

# ========== ✏️ 练习 ==========
# 1. 用 setex 写一个"短信验证码"功能：save_code(phone, code) 存5分钟，
#    verify_code(phone, code) 校验（对则删除并返回True，错返回False）
# 2. 用 incr 实现"接口限流"：allow_request(user_id) 每分钟最多 10 次，
#    超过返回 False（提示：key 里带分钟数，配合 expire）
# 3. （思考）缓存模式里，如果数据库里的数据【更新】了，缓存还是旧的，
#    怎么办？（这就是著名的"缓存一致性"问题，注释写下你的思路）
