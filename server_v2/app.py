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

import os
engine = create_engine(os.getenv("DB_URL", "sqlite:///server_v2.db"))  # 测试用 env 注入独立库

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

# ============================================================
# Step2: 聊天接口（JWT 守卫 + Redis 限流 + SSE 流式）
# ============================================================
import json
import urllib.request

from fastapi.responses import StreamingResponse
from .redis_client import allow_request

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")  # 容器里注入 host.docker.internal
MODEL = "qwen2.5:3b"

class ChatReq(BaseModel):
    message: str
    history: list[dict] = []

def rate_limit_guard(username: str = Depends(get_current_user)) -> str:
    """依赖链：先验 JWT，再查限流（Depends 里套 Depends）"""
    if not allow_request(username, limit=20, window=60):
        raise HTTPException(status_code=429, detail="请求太频繁，请稍后再试")
    return username

def sse_chat(messages: list[dict]):
    """生成器：逐行读 Ollama 流式响应，包装成 SSE 格式"""
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps({"model": MODEL, "messages": messages, "stream": True}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        for line in resp:
            chunk = json.loads(line)
            if content := chunk.get("message", {}).get("content"):
                yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
    yield 'data: {"done": true}\n\n'

@app.post("/chat/stream")
def chat_stream(req: ChatReq, username: str = Depends(rate_limit_guard)):
    """守卫链：JWT 401 → 限流 429 → 放行"""
    messages = [{"role": "system", "content": "你是一个简洁的助手"}]
    messages += req.history[-10:]            # 只带最近10条历史（上下文控制）
    messages.append({"role": "user", "content": req.message})
    return StreamingResponse(sse_chat(messages), media_type="text/event-stream")

# ============================================================
# Step3: 聊天历史持久化（按用户隔离）
# ============================================================
from datetime import datetime, timezone

class ChatSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chatsession.id", index=True)
    role: str          # "user" | "assistant"
    content: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ChatReqV2(BaseModel):
    message: str
    session_id: int | None = None   # 不带 = 新会话

def get_owned_session(session_id: int, username: str, s: Session) -> ChatSession:
    """查会话 + 校验归属（防 IDOR：不能靠猜 ID 看别人的聊天记录）"""
    session = s.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    user = s.exec(select(User).where(User.username == username)).first()
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该会话")
    return session

def sse_chat_persist(messages: list[dict], session_id: int):
    """流式输出 + 边流边累积，结束后落库"""
    full = []
    yield f"data: {json.dumps({'session_id': session_id})}\n\n"   # 先告诉前端会话ID
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps({"model": MODEL, "messages": messages, "stream": True}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        for line in resp:
            chunk = json.loads(line)
            if content := chunk.get("message", {}).get("content"):
                full.append(content)
                yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
    # 流结束后：assistant 回复落库
    with Session(engine) as s:
        s.add(Message(session_id=session_id, role="assistant", content="".join(full)))
        s.commit()
    yield 'data: {"done": true}\n\n'

@app.post("/v2/chat/stream")
def chat_stream_v2(req: ChatReqV2, username: str = Depends(rate_limit_guard)):
    with Session(engine) as s:
        # ① 确定会话（新/旧）+ 校验归属
        if req.session_id is None:
            user = s.exec(select(User).where(User.username == username)).first()
            session = ChatSession(user_id=user.id, title=req.message[:20])
            s.add(session)
            s.commit()
            s.refresh(session)
            history = []
        else:
            session = get_owned_session(req.session_id, username, s)
            rows = s.exec(
                select(Message).where(Message.session_id == session.id).order_by(Message.id)
            ).all()
            history = [{"role": m.role, "content": m.content} for m in rows]
        # ② 用户消息落库
        s.add(Message(session_id=session.id, role="user", content=req.message))
        s.commit()
        session_id = session.id

    messages = [{"role": "system", "content": "你是一个简洁的助手"}]
    messages += history[-10:]
    messages.append({"role": "user", "content": req.message})
    return StreamingResponse(sse_chat_persist(messages, session_id), media_type="text/event-stream")

@app.get("/sessions")
def list_sessions(username: str = Depends(get_current_user)):
    """只返回【当前用户】的会话列表（WHERE user_id = 我）"""
    with Session(engine) as s:
        user = s.exec(select(User).where(User.username == username)).first()
        rows = s.exec(
            select(ChatSession).where(ChatSession.user_id == user.id).order_by(ChatSession.id.desc())
        ).all()
        return {"data": [{"id": r.id, "title": r.title, "created_at": r.created_at} for r in rows]}

@app.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: int, username: str = Depends(get_current_user)):
    with Session(engine) as s:
        get_owned_session(session_id, username, s)   # 先验归属
        rows = s.exec(
            select(Message).where(Message.session_id == session_id).order_by(Message.id)
        ).all()
        return {"data": [{"role": m.role, "content": m.content} for m in rows]}
