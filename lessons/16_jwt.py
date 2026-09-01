"""
第 16 课：JWT（JSON Web Token）—— 无状态认证
运行方式：python3 16_jwt.py（纯概念演示，不用启动服务）

JWT 结构：xxxxx.yyyyy.zzzzz 三段，用点连接
  ① Header（头部）：算法信息
  ② Payload（载荷）：用户信息 + 过期时间  ← 重点：不加密，谁都能看！
  ③ Signature（签名）：防篡改的封印
"""
import base64
import hashlib
import hmac
import json
import time

SECRET = "my-secret-key"  # 服务器的私藏密钥（生产放环境变量！）

# ---------- 工具：base64url 编解码（JWT 的编码方式）----------
def b64encode(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

def b64decode(s: str) -> dict:
    s += "=" * (-len(s) % 4)  # 补回被去掉的填充
    return json.loads(base64.urlsafe_b64decode(s))

# ---------- 签发 JWT（登录成功后服务器做的事）----------
def create_jwt(username: str, expires_in: int = 3600) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": username,                          # 主体：这个 token 是谁的
        "exp": int(time.time()) + expires_in,     # 过期时间（1小时后）
        "iat": int(time.time()),                  # 签发时间
    }
    # ①② 段拼起来，③ 用密钥对它们签名
    signing_input = f"{b64encode(header)}.{b64encode(payload)}"
    signature = hmac.new(SECRET.encode(), signing_input.encode(), hashlib.sha256)
    return f"{signing_input}.{base64.urlsafe_b64encode(signature.digest()).rstrip(b'=').decode()}"

# ---------- 验证 JWT（每个请求来了，服务器做的事）----------
def verify_jwt(token: str) -> dict:
    """验签名 + 验过期。返回用户信息；无效则抛异常"""
    header_b64, payload_b64, signature = token.split(".")

    # 关键：用同样的密钥重新算一遍签名，和 token 里带的对比
    expected = hmac.new(SECRET.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256)
    actual = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
    if not hmac.compare_digest(expected.digest(), actual):
        raise ValueError("❌ 签名不对：token 被篡改或不是本服务器签发")

    payload = b64decode(payload_b64)
    if payload["exp"] < time.time():
        raise ValueError("❌ token 已过期")
    return payload

# ========== 演示 ==========
print("=== 1. 签发一个 JWT ===")
token = create_jwt("xiaoming")
print(token)
h, p, s = token.split(".")
print(f"\n三段拆解:")
print(f"  Header  : {b64decode(h)}")
print(f"  Payload : {b64decode(p)}   ← 用户信息直接在里面，不用查库！")
print(f"  Signature: {s[:20]}...（一串乱码，防篡改封印）")

print("\n=== 2. 正常验证 ===")
print(f"✅ 通过: {verify_jwt(token)}")

print("\n=== 3. 黑客篡改 payload（把 xiaoming 改成 admin）===")
evil_payload = b64encode({"sub": "admin", "exp": int(time.time()) + 3600, "iat": int(time.time())})
evil_token = f"{h}.{evil_payload}.{s}"  # 签名沿用的还是旧的
try:
    verify_jwt(evil_token)
except ValueError as e:
    print(e, "← 篡改被抓！")

print("\n=== 4. 黑客不知道密钥，自己造签名也没用 ===")
fake_sig = base64.urlsafe_b64encode(b"fake").decode().rstrip("=")
try:
    verify_jwt(f"{h}.{evil_payload}.{fake_sig}")
except ValueError as e:
    print(e, "← 伪造被抓！")
