"""
第 24 课：消息队列（MQ）—— 用 Redis List 实现生产者-消费者
运行方式：.venv/bin/python 24_message_queue.py（确保 redis-demo 容器在跑）

核心思想：慢操作不要阻塞主流程，扔进队列，后台慢慢处理
  同步时代: 用户注册 → 等发邮件2秒 → 才看到"注册成功"（体验差）
  队列时代: 用户注册 → 任务扔进队列(0.001秒) → 立即返回 ✅
                  后台 worker 慢慢发邮件，用户无感
"""
import json
import threading
import time

import redis

r = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)
QUEUE = "queue:email"   # 队列就是一条 Redis List
r.delete(QUEUE)

# ---------- 慢操作：发邮件要 2 秒 ----------
def send_email(to: str, subject: str):
    time.sleep(2)   # 模拟：连邮件服务器、渲染模板……总之很慢
    print(f"      📧 邮件已发出 → {to} 《{subject}》")

# ---------- 消费者（worker）：死循环盯着队列，有活就干 ----------
def consumer():
    print("👷 worker 启动，等待任务……")
    while True:
        # BRPOP：阻塞式弹出——队列空就挂起等待（不空转烧CPU），有任务立刻醒
        result = r.brpop(QUEUE, timeout=5)
        if result is None:
            print("👷 5秒没活干，继续等……")
            continue
        _, task_json = result            # Redis List 弹出的任务
        task = json.loads(task_json)
        print(f"   👷 领到任务: {task}")
        send_email(task["to"], task["subject"])

# ---------- 生产者：模拟 3 个用户几乎同时注册 ----------
if __name__ == "__main__":
    # 消费者跑在后台线程（真实世界：worker 是独立的进程/机器）
    t = threading.Thread(target=consumer, daemon=True)
    t.start()
    time.sleep(0.5)

    print("\n--- 三个用户几乎同时注册 ---")
    t0 = time.perf_counter()
    for i in range(1, 4):
        # API 接口里只干一件事：把任务扔进队列，立即返回！
        task = {"to": f"user{i}@test.com", "subject": "欢迎注册"}
        r.lpush(QUEUE, json.dumps(task))
        print(f"🚀 用户{i} 注册接口已返回（耗时 {time.perf_counter()-t0:.3f}s，没等发邮件）")

    print(f"\n✅ 三个接口全部返回完毕，总耗时 {time.perf_counter()-t0:.3f} 秒")
    print("   （同步时代要等 6 秒！邮件在后台慢慢发：）\n")
    time.sleep(7)   # 等 worker 把 3 封邮件发完再退出

# ========== ✏️ 练习 ==========
# 1. 再加一个"发短信"队列 queue:sms，让同一个 worker 同时监听两条队列
#    （提示：brpop 可以传多个 key，哪个有活弹哪个）
# 2. 如果 worker 处理到一半崩溃了，队列里的任务会怎样？
#    （提示：BRPOP 弹出来任务就没了 → 注释写下这个可靠性问题，
#     这就是专业 MQ（RabbitMQ/Kafka）存在的意义：消息确认机制 ack）
