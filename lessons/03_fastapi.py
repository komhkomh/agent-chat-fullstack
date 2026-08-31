"""
第三课：FastAPI —— 你的第一个后端接口
启动方式（在 learn-python 目录下）：
    .venv/bin/uvicorn 03_fastapi:app --reload
然后打开浏览器：http://127.0.0.1:8000/docs   ← 自动生成的接口文档，重点看这个！
按 Ctrl+C 停止服务
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="我的第一个 API")

# 假数据库（先用 list 顶替，第 4 课换真数据库）
users = [
    {"id": 1, "name": "小明", "role": "dev"},
    {"id": 2, "name": "小红", "role": "admin"},
    {"id": 3, "name": "老王", "role": "dev"},
]

# ---------- 1. 最简单的 GET ----------
@app.get("/")
def root():
    return {"message": "Hello, 后端世界！"}

# ---------- 2. GET 列表 + 查询参数（?role=dev）----------
@app.get("/users")
def list_users(role: str | None = None):
    # 访问 /users → role 是 None；访问 /users?role=dev → role 是 "dev"
    if role:
        return [u for u in users if u["role"] == role]
    return users

# ---------- 3. GET 单个 + 路径参数（/users/2）----------
@app.get("/users/{user_id}")
def get_user(user_id: int):  # 类型标注 int：FastAPI 自动校验+转换，传 "abc" 会直接返回 422
    for u in users:
        if u["id"] == user_id:
            return u
    raise HTTPException(status_code=404, detail="用户不存在")  # 标准错误返回

# ---------- 4. POST 创建（接收 JSON 请求体）----------
class UserCreate(BaseModel):  # 请求体的"数据模型"，类似 Dart 的 data class
    name: str
    role: str = "dev"  # 不传就默认 dev
    age: int

@app.post("/users", status_code=201)
def create_user(payload: UserCreate):
    new_user = {"id": len(users) + 1, "name": payload.name, "role": payload.role}
    users.append(new_user)
    return new_user

@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    for i, u in enumerate(users):
        if u["id"] == user_id:
            users.pop(i)
            return {"message": "删除成功"}
    raise HTTPException(status_code=404, detail="用户不存在")

@app.get("/stats")
def get_stats():
    dev_count = sum(1 for u in users if u["role"] == "dev")
    admin_count = sum(1 for u in users if u["role"] == "admin")
    return {"total": len(users), "dev_count": dev_count, "admin_count": admin_count}

# ========== ✏️ 课后练习 ==========
# 1. 加一个 DELETE /users/{user_id} 接口，删除用户，找不到返回 404
#    提示: users.remove(u) 或 users.pop(index)
# 2. 加一个 GET /stats 接口，返回 {"total": 3, "dev_count": 2, "admin_count": 1}
# 3. 给 UserCreate 加一个 age 字段（int，必填），POST 后返回的用户里也带上
