"""
第 4 课 B：FastAPI 连接数据库 —— 真实的后端雏形
启动方式：
    .venv/bin/uvicorn 04b_fastapi_db:app --reload
测试：http://127.0.0.1:8000/docs
"""
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="带数据库的 API")
DB_FILE = "app.db"  # 复用 04a 生成的数据库文件

# ---------- 数据库小助手 ----------
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.on_event("startup")
def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'dev'
        )
    """)
    conn.commit()
    conn.close()

# ---------- 接口 ----------
class UserCreate(BaseModel):
    name: str
    role: str = "dev"

@app.get("/users")
def list_users(role: str | None = None, name: str | None = None):
    conn = get_conn()
    if role:
        rows = conn.execute("SELECT * FROM users WHERE role = ?", (role,)).fetchall()
    elif name:
        rows = conn.execute("SELECT * FROM users WHERE name LIKE ?", (f"%{name}%",)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return [dict(r) for r in rows]  # Row 对象转成 dict 才能变 JSON

@app.get("/users/{user_id}")
def get_user(user_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return dict(row)

@app.post("/users", status_code=201)
def create_user(payload: UserCreate):
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO users (name, role) VALUES (?, ?)",
        (payload.name, payload.role),
    )
    conn.commit()
    new_id = cursor.lastrowid  # 拿到数据库自动生成的 id
    conn.close()
    return {"id": new_id, "name": payload.name, "role": payload.role}

@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    conn = get_conn()
    cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    if cursor.rowcount == 0:  # rowcount = 受影响的行数，0 说明没找到
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"message": f"已删除 id={user_id}"}


@app.put("/users/{user_id}")
def update_user(user_id: int, payload: UserCreate):
    conn = get_conn()
    conn.execute(
        "UPDATE users SET name = ?, role = ? WHERE id = ?",
        (payload.name, payload.role, user_id),
    )
    conn.commit()
    conn.close()
# ========== ✏️ 课后练习 ==========
# 1. 加一个 PUT /users/{user_id} 接口，修改用户的 name 和 role（UPDATE 语句）
# 2. 给 GET /users 加一个 name 查询参数，支持模糊搜索：
#    提示: WHERE name LIKE ?  参数用 f"%{name}%"
# 3. （思考）对比 03 课的 list 版本，说说数据库版解决了什么问题？注释在代码里
