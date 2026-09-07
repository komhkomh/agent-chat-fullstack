"""
第 18 课：API 设计规范 —— 分页 / 统一错误 / 版本管理
启动：.venv/bin/uvicorn 18_api_design:app --port 8011
测试：http://127.0.0.1:8011/docs

为什么需要规范：接口是"和前端/第三方的合同"，合同随便写，
以后改一个字都可能让别人的 App 崩溃。
"""
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="规范化的 API", root_path="")

# ---------- 造 95 个假用户 ----------
USERS = [{"id": i, "name": f"用户{i}", "role": "dev" if i % 3 else "admin"}
         for i in range(1, 96)]

# ============================================================
# 规范1：统一错误格式 —— 所有错误都长一个样
# ============================================================
class ApiError(HTTPException):
    """业务错误统一格式：{"error": {"code": 机器可读的码, "message": 给人看的}}"""
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code)
        self.code = code
        self.message = message

@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    """拦截 ApiError，转成统一格式返回（FastAPI 的异常处理器机制）"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )

# ============================================================
# 规范2：版本管理 —— URL 带 /v1，以后改接口不坑老用户
# ============================================================
# ============================================================
# 规范3：分页 —— 绝不一次返回全量数据
# ============================================================
@app.get("/v1/users")
def list_users(
    page: int = Query(default=1, ge=1),           # 第几页（从1开始）
    page_size: int = Query(default=10, ge=1, le=50),  # 每页几条（上限50防滥用）
):
    total = len(USERS)
    start = (page - 1) * page_size
    items = USERS[start:start + page_size]
    if not items and page > 1:
        raise ApiError(404, "PAGE_OUT_OF_RANGE", f"第 {page} 页不存在，一共只有 {(total + page_size - 1) // page_size} 页")
    # 分页接口的标准返回结构：数据 + 分页元信息
    return {
        "data": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }

@app.get("/v1/users/{user_id}")
def get_user(user_id: int):
    for u in USERS:
        if u["id"] == user_id:
            return {"data": u}   # 成功也统一包一层 data
    raise ApiError(404, "USER_NOT_FOUND", f"用户 {user_id} 不存在")

# ========== ✏️ 练习 ==========
# 1. 给 /v1/users 加 role 筛选参数（/v1/users?role=dev），筛选逻辑要在分页【之前】
# 2. 写一个 /v2/users，返回结构改成 {"users": [...], "meta": {...}}——
#    体会：v1 继续工作，v2 用新结构，两个版本共存（版本管理的意义）
# 3. （思考）cursor 分页（用上一页最后一个 id 当起点）比 page 分页
#    更适合"无限滚动"场景（你的聊天 App），为什么？注释回答
