"""JWT 工具（第16课的手写实现，生产环境推荐换成 PyJWT 库）"""
import base64
import hashlib
import hmac
import json
import os
import time

SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")  # 生产必须环境变量注入！


def _b64e(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).rstrip(b"=").decode()


def _b64d(s: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)))


def create_token(username: str, expires_in: int = 3600) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": username, "exp": int(time.time()) + expires_in, "iat": int(time.time())}
    signing_input = f"{_b64e(header)}.{_b64e(payload)}"
    sig = hmac.new(SECRET.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"


def verify_token(token: str) -> str:
    """验签名+过期，返回 username；无效抛 ValueError"""
    try:
        h_b64, p_b64, sig = token.split(".")
        expected = hmac.new(SECRET.encode(), f"{h_b64}.{p_b64}".encode(), hashlib.sha256).digest()
        actual = base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4))
        if not hmac.compare_digest(expected, actual):
            raise ValueError("签名无效")
        payload = _b64d(p_b64)
        if payload["exp"] < time.time():
            raise ValueError("已过期")
        return payload["sub"]
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise ValueError(f"token 无效: {e}")
