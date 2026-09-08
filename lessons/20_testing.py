"""
第 20 课：给后端写测试 —— 用 pytest + TestClient
运行方式：.venv/bin/pytest 20_testing.py -v

核心概念：
① TestClient：不用启动 uvicorn，直接在进程内调用你的 FastAPI app
② 每个 test_ 函数 = 一条独立测试用例：准备 → 执行 → 断言(assert)
③ 测试是"会执行的文档"，更是重构和 AI 生成代码的安全网
"""
import importlib.util
import uuid

from fastapi.testclient import TestClient

# 15_auth 文件名以数字开头，不能直接 import，用 importlib 加载
spec = importlib.util.spec_from_file_location("auth_app", "15_auth.py")
auth_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth_module)

client = TestClient(auth_module.app)

# ---------- 准备：每个测试用独立的随机用户名，互不干扰 ----------
def random_user():
    return {"username": f"user_{uuid.uuid4().hex[:8]}", "password": "mima123"}

# ---------- 测试 1：注册成功 ----------
def test_register_success():
    user = random_user()
    resp = client.post("/register", json=user)
    assert resp.status_code == 201, f"期望201，实际{resp.status_code}: {resp.text}"

# ---------- 测试 2：重复注册被 409 拒绝 ----------
def test_register_duplicate():
    user = random_user()
    client.post("/register", json=user)          # 第一次：成功
    resp = client.post("/register", json=user)   # 第二次：应 409
    assert resp.status_code == 409

# ---------- 测试 3：错误密码登录被 401 拒绝 ----------
def test_login_wrong_password():
    user = random_user()
    client.post("/register", json=user)
    resp = client.post("/login", json={"username": user["username"], "password": "wrong"})
    assert resp.status_code == 401

# ---------- 测试 4：完整流程：注册 → 登录 → 带token访问 → 通过 ----------
def test_full_auth_flow():
    user = random_user()
    client.post("/register", json=user)
    token = client.post("/login", json=user).json()["token"]
    resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert user["username"] in resp.json()["message"]

# ---------- 测试 5：不带 token 访问受保护接口被 401 ----------
def test_me_without_token():
    resp = client.get("/me")
    assert resp.status_code == 401

# ---------- 测试 6：伪造 token 被 401 ----------
def test_me_with_fake_token():
    resp = client.get("/me", headers={"Authorization": "Bearer fake_token_123"})
    assert resp.status_code == 401

# ========== ✏️ 练习 ==========
# 1. 给 15 课的 /logout（练习1你写的）补一条测试：
#    登录 → logout → 再用旧 token 访问 /me → 应 401
# 2. 故意把 15_auth.py 里 401 改成 400，重跑测试——
#    体会"测试当场抓住改动"的感觉（改完记得改回来）
# 3. （思考）为什么测试里要用 random_user() 而不是固定的 "xiaoming"？
