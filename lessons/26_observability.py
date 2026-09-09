"""
第 26 课：可观测性三支柱 —— 日志(Logs) / 指标(Metrics) / 链路追踪(Traces)
启动：.venv/bin/uvicorn 26_observability:app --port 8012

定义：可观测性（Observability）= 通过系统外部输出（日志、指标、追踪）
推断系统内部状态的能力。微服务时代没有它 = 盲人开飞机。
"""
import time
import uuid
from collections import defaultdict

from fastapi import FastAPI, Request

app = FastAPI()

# ---------- 支柱② 指标(Metrics)：内存里的计数器 ----------
# 定义：按时间聚合的数值数据，回答"整体怎么样"（QPS/错误率/延迟分布）
METRICS = defaultdict(int)
METRICS["request_total"] = 0
METRICS["error_total"] = 0

# ---------- 支柱③ 链路追踪(Traces)：给每个请求发"身份证号" ----------
# 定义：一个请求穿过多个组件的完整路径记录，回答"这一次请求经历了什么"
@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    # ① 生成或继承 Trace ID（微服务里：上游传下来就用上游的）
    trace_id = request.headers.get("X-Trace-ID") or uuid.uuid4().hex[:8]

    t0 = time.perf_counter()
    response = await call_next(request)
    cost_ms = (time.perf_counter() - t0) * 1000

    # 支柱① 日志(Logs)：结构化记录"发生了什么"
    # 关键：每条日志都带 trace_id —— 这是日志能被"串成链路"的原因
    METRICS["request_total"] += 1
    if response.status_code >= 400:
        METRICS["error_total"] += 1
    print(f'[trace={trace_id}] {request.method} {request.url.path} '
          f'→ {response.status_code} ({cost_ms:.1f}ms)')

    # Trace ID 回传给调用方（全链路透传的规矩）
    response.headers["X-Trace-ID"] = trace_id
    return response

# ---------- 业务接口 ----------
@app.get("/orders/{order_id}")
def get_order(order_id: int, request: Request):
    # 模拟：这个接口内部还要调用"库存服务"（微服务里是另一个进程）
    # Trace ID 会跟着传过去，于是两个服务的日志能拼成一条链
    if order_id > 100:
        # 注意：FastAPI 不支持 Flask 风格的 (body, status) 元组返回
        # 元组会被整体 JSON 序列化，状态码仍是 200 → 要用 JSONResponse
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "订单不存在"}, status_code=404)
    return {"order_id": order_id, "item": "机械键盘", "amount": 299}

@app.get("/metrics")
def metrics():
    """指标暴露端点——Prometheus 会定时来抓这个（拉取模式，和 Kafka 一样）"""
    total = METRICS["request_total"]
    errors = METRICS["error_total"]
    return {
        "request_total": total,
        "error_total": errors,
        "error_rate": f"{errors / total * 100:.1f}%" if total else "0%",
    }

# ========== ✏️ 练习 ==========
# 1. 在 /metrics 里加 avg_latency_ms（在 middleware 里累计总耗时）
# 2. （思考）为什么 Trace ID 要"上游有就用上游的"？如果每层都自己生成会怎样？
