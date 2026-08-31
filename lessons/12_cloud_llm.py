"""
第 12 课：接入云端大模型（DeepSeek，OpenAI 兼容格式）
前置：
  1. 去 https://platform.deepseek.com 注册 → 充值 → 创建 API Key
  2. 终端设置环境变量：export DEEPSEEK_API_KEY="sk-你的key"
运行方式：python3 12_cloud_llm.py
"""
import json
import os
import urllib.request

API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not API_KEY:
    raise SystemExit("❌ 请先设置环境变量：export DEEPSEEK_API_KEY='sk-你的key'")

URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

def chat(messages: list[dict]) -> str:
    """调云端模型——和本地版唯一的区别：URL + Authorization 头"""
    payload = {"model": MODEL, "messages": messages, "stream": False}
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",  # ← 云端特有：API Key 鉴权
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
        # OpenAI 格式"方言"：回复包在 choices 数组里
        return data["choices"][0]["message"]["content"]

# 和本地模型完全一样的调用方式
print(chat([{"role": "user", "content": "用一句话解释什么是 RAG"}]))

# 本地 vs 云端随时切换：只改 URL/MODEL/鉴权，业务代码不动——
# 这就是"OpenAI 兼容格式"这个事实标准的威力
