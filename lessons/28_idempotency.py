"""
第 28 课：幂等性 —— 用 Redis SET NX 实现支付接口幂等
运行方式：.venv/bin/python 28_idempotency.py（需 Redis 运行）

演示：同一个 Idempotency-Key 请求 3 次，只真正执行 1 次扣款
"""
import time
import uuid

import redis

r = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)
r.flushdb()  # 演示环境，清空

# ---------- 模拟账户 ----------
def get_balance() -> int:
    return int(r.get("account:balance") or 1000)

def deduct(amount: int):
    """真正的扣款动作（有副作用！）"""
    r.decrby("account:balance", amount)

# ---------- 非幂等版（反面教材）----------
def pay_naive(amount: int) -> dict:
    deduct(amount)
    return {"status": "ok", "balance": get_balance()}

# ---------- 幂等版 ----------
import json

def pay_idempotent(idempotency_key: str, amount: int) -> dict:
    cache_key = f"idem:{idempotency_key}"
    # SET NX：key 不存在才写入（首次请求）——返回 True 表示"我是第一次"
    is_first = r.set(cache_key, "PROCESSING", nx=True, ex=3600)
    if not is_first:
        cached = r.get(cache_key)
        if cached == "PROCESSING":
            return {"status": "processing", "note": "相同请求正在处理中"}
        return {**json.loads(cached), "note": "命中幂等缓存，未重复扣款"}
    # 首次：执行真实扣款，缓存结果
    deduct(amount)
    result = {"status": "ok", "balance": get_balance()}
    r.set(cache_key, json.dumps(result), ex=3600, xx=True)  # xx：只覆盖已存在的占位
    return result

# ========== 演示 ==========
print("=== ① 非幂等版：网络重试 3 次 ===")
r.set("account:balance", 1000)
for i in range(3):
    print(f"   第{i+1}次调用: {pay_naive(100)}")
print(f"   💥 扣了 3 次款，余额 {get_balance()}（应该是 900！）\n")

print("=== ② 幂等版：同一 Idempotency-Key 重试 3 次 ===")
r.set("account:balance", 1000)
key = str(uuid.uuid4())   # 客户端为"这笔支付"生成的唯一标识
for i in range(3):
    print(f"   第{i+1}次调用: {pay_idempotent(key, 100)}")
print(f"   ✅ 只扣了 1 次，余额 {get_balance()}\n")

print("=== ③ 幂等版：换一个新 key = 新的一笔支付 ===")
print(f"   {pay_idempotent(str(uuid.uuid4()), 100)}")
print(f"   余额 {get_balance()}（正常再扣 100）")

# ========== ✏️ 练习 ==========
# 1. 给 15 课的注册接口想一个"幂等保障"方案（提示：它其实已经天然幂等了，为什么？）
# 2. （思考）PROCESSING 占位的作用是什么？如果并发两个相同 key 请求同时到达会怎样？
