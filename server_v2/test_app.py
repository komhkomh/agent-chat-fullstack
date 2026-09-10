"""
实战回填 Step4：pytest 测试套件
运行：.venv/bin/pytest server_v2/test_app.py -v
关键实践：DB_URL 环境变量注入独立测试库，与开发数据隔离
"""
import os
import uuid

os.environ["DB_URL"] = "sqlite:///test_v2.db"   # 必须在 import app 之前设置！
os.environ["JWT_SECRET"] = "test-secret"

from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from server_v2.app import app, engine

SQLModel.metadata.create_all(engine)  # TestClient 不触发 startup 事件，手动建表
from server_v2.redis_client import allow_request, pool

client = TestClient(app)

def random_user():
    return {"username": f"u_{uuid.uuid4().hex[:8]}", "password": "mima123"}

def auth_header(user):
    client.post("/register", json=user)
    token = client.post("/login", json=user).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# ---------- 认证 ----------
def test_register_and_login():
    user = random_user()
    assert client.post("/register", json=user).status_code == 201
    resp = client.post("/login", json=user)
    assert resp.status_code == 200
    assert "access_token" in resp.json()

def test_register_duplicate_409():
    user = random_user()
    client.post("/register", json=user)
    assert client.post("/register", json=user).status_code == 409

def test_login_wrong_password_401():
    user = random_user()
    client.post("/register", json=user)
    resp = client.post("/login", json={"username": user["username"], "password": "wrong"})
    assert resp.status_code == 401

def test_me_requires_token():
    assert client.get("/me").status_code in (401, 422)

def test_me_with_token():
    user = random_user()
    resp = client.get("/me", headers=auth_header(user))
    assert resp.status_code == 200
    assert user["username"] in resp.json()["message"]

# ---------- 会话隔离 & IDOR ----------
def test_sessions_isolated_between_users():
    user_a, user_b = random_user(), random_user()
    client.post("/register", json=user_a)   # 先注册，否则查不到 id
    # A 有会话（直接插库模拟，避免调真实 LLM）
    from server_v2.app import ChatSession, User, engine
    from sqlmodel import Session, select
    with Session(engine) as s:
        ua = s.exec(select(User).where(User.username == user_a["username"])).first()
        s.add(ChatSession(user_id=ua.id, title="A的私密聊天"))
        s.commit()
    # B 的列表必须为空
    resp = client.get("/sessions", headers=auth_header(user_b))
    assert resp.json()["data"] == []

def test_idor_access_other_user_session_403():
    user_a, user_b = random_user(), random_user()
    client.post("/register", json=user_a)   # 先注册
    from server_v2.app import ChatSession, User, engine
    from sqlmodel import Session, select
    with Session(engine) as s:
        ua = s.exec(select(User).where(User.username == user_a["username"])).first()
        sess = ChatSession(user_id=ua.id, title="A的私密聊天")
        s.add(sess)
        s.commit()
        s.refresh(sess)
        sid = sess.id
    # B 试图访问 A 的会话 → 403
    resp = client.get(f"/sessions/{sid}/messages", headers=auth_header(user_b))
    assert resp.status_code == 403

# ---------- 限流（单元级，不走真实接口）----------
def test_rate_limiter():
    key_user = f"test_{uuid.uuid4().hex[:6]}"
    assert allow_request(key_user, limit=2, window=60) is True
    assert allow_request(key_user, limit=2, window=60) is True
    assert allow_request(key_user, limit=2, window=60) is False   # 第3次被拒

# ---------- 聊天接口守卫（不调真实 LLM）----------
def test_chat_requires_token():
    resp = client.post("/v2/chat/stream", json={"message": "hi"})
    assert resp.status_code in (401, 422)

# 清理测试痕迹
def test_zzz_cleanup():
    for k in pool.keys("rate_limit:test_*"):
        pool.delete(k)
