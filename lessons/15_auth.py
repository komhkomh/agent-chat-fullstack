"""
第 15 课：用户认证（Auth）—— 注册/登录/Token/守卫
启动：.venv/bin/uvicorn 15_auth:app --port 8000
测试：http://127.0.0.1:8000/docs

四个核心概念：
① 密码绝不存明文 → 哈希（不可逆）+ 盐（防彩虹表）
② 登录成功 → 发 Token（通行证）
③ 之后的请求带 Token → 服务器认"证"不认"密码"
④ 路由守卫：用 Depends 把"验票"逻辑做成可复用的门卫
"""
import hashlib
import secrets
import sqlite3

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

DB_FILE = "auth.db"
app = FastAPI(title="认证系统")

# ---------- 建表：注意没有"密码"列，只有 hash 和 salt ----------
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

conn = get_conn()
conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt          TEXT NOT NULL
    )
""")
conn.commit()
conn.close()

# ---------- ① 密码哈希：加盐 + 慢哈希（PBKDF2，10万次迭代）----------
def hash_password(password: str, salt: str) -> str:
    """把(密码+盐)搅拌10万次，输出不可逆的哈希值"""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), iterations=100_000
    ).hex()

# ---------- 内存 Token 表：token -> username（学习用；生产用 Redis/JWT）----------
TOKENS: dict[str, str] = {}

# ---------- 注册 ----------
class RegisterReq(BaseModel):
    username: str
    password: str

@app.post("/register", status_code=201)
def register(req: RegisterReq):
    salt = secrets.token_hex(16)          # 每个用户随机一把盐
    pwd_hash = hash_password(req.password, salt)
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (req.username, pwd_hash, salt),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="用户名已存在")
    finally:
        conn.close()
    return {"message": f"用户 {req.username} 注册成功"}

# ---------- ② 登录：验证哈希 → 发 Token ----------
class LoginReq(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(req: LoginReq):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (req.username,)).fetchone()
    conn.close()
    # 注意：不告诉攻击者"到底是用户名错了还是密码错了"——统一说"用户名或密码错误"
    if row is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if hash_password(req.password, row["salt"]) != row["password_hash"]:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = secrets.token_hex(24)          # 随机生成通行证
    TOKENS[token] = req.username           # 服务端记下：这张证是谁的
    return {"token": token, "message": "登录成功"}

# ---------- ④ 路由守卫：可复用的"验票门卫" ----------
def get_current_user(authorization: str = Header(default="")) -> str:
    """FastAPI 依赖注入：每个受保护接口都会先经过它"""
    # 约定请求头格式：Authorization: Bearer <token>
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少 Token")
    token = authorization.removeprefix("Bearer ")
    username = TOKENS.get(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    return username  # 返回值会被注入到接口函数的参数里！

# ---------- ③ 受保护的接口 ----------
@app.get("/me")
def get_me(username: str = Depends(get_current_user)):
    """只要写上 Depends(get_current_user)，这个接口就有了门卫"""
    return {"message": f"你好，{username}！你已通过认证"}

@app.get("/admin")
def admin_only(username: str = Depends(get_current_user)):
    return {"message": f"{username}，这是机密区域"}

# ========== ✏️ 练习 ==========
# 1. 加 POST /logout：把 token 从 TOKENS 里删掉（通行证作废）
# 2. 现在 TOKENS 在内存，重启就全失效。把它存进 SQLite（token 表）
# 3. （思考）现在的 token 永不过期，有什么问题？怎么加"过期时间"？
