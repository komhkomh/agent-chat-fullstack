"""
实战回填：生产级聊天后端 v2
技术栈：FastAPI + SQLModel + JWT + Redis + SSE + pytest + Docker
启动：JWT_SECRET=xxx .venv/bin/uvicorn server_v2.app:app --port 8020
"""
import hashlib
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select

app = FastAPI(title="Agent Chat API v2")

# ---------- 数据层（SQLModel）----------
class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    salt: str

engine = create_engine("sqlite:///server_v2.db")

@app.on_event("startup")
def init_db():
    SQLModel.metadata.create_all(engine)

# ---------- 密码工具（第15课的配方）----------
def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()

# ---------- JWT 守卫 ----------
from .jwt_utils import create_token, verify_token

def get_current_user(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少 Token")
    try:
        return verify_token(authorization.removeprefix("Bearer "))
    except ValueError:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

# ---------- 认证接口 ----------
class AuthReq(BaseModel):
    username: str
    password: str

@app.post("/register", status_code=201)
def register(req: AuthReq):
    salt = secrets.token_hex(16)
    with Session(engine) as s:
        if s.exec(select(User).where(User.username == req.username)).first():
            raise HTTPException(status_code=409, detail="用户名已存在")
        s.add(User(username=req.username, password_hash=hash_password(req.password, salt), salt=salt))
        s.commit()
    return {"message": "注册成功"}

@app.post("/login")
def login(req: AuthReq):
    with Session(engine) as s:
        user = s.exec(select(User).where(User.username == req.username)).first()
    if user is None or hash_password(req.password, user.salt) != user.password_hash:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_token(req.username)
    return {"access_token": token, "token_type": "bearer", "expires_in": 3600}

@app.get("/me")
def get_me(username: str = Depends(get_current_user)):
    return {"message": f"你好，{username}（JWT 验证通过，没查数据库）"}
