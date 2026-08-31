"""
第 5 课：后端调用 LLM —— 你的接口开始"长脑子"
前置：确保 Ollama 服务在运行（ollama serve），且已 pull 模型
运行方式：python3 05_llm_api.py
"""
import json
import urllib.request


# ========== 核心概念：LLM 就是一个 HTTP 接口 ==========
# 和你在第 3/4 课写的 API 一模一样：
#   POST 一个 JSON（对话消息）→ 返回一个 JSON（模型的回复）
# Ollama 把这件事跑在你本机：http://127.0.0.1:11434

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5:3b"  # 换成你 pull 的模型名

def chat(messages: list[dict], temperature: float = 0.7) -> str:
    """给 LLM 发一组消息，返回它的回复文本"""
    payload = {
        "model": MODEL,
        "messages": messages,       # 对话历史（下面详解）
        "temperature": temperature,  # 0=稳定保守，1=发散创意
        "stream": False,            # 先学一次性返回；流式（打字机效果）以后再说
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())["message"]["content"]

# ---------- 1. 最小调用：一条 user 消息 ----------
print("=== 1. 最小调用 ===")
answer = chat([{"role": "user", "content": "用一句话解释什么是 API"}])
print(answer)

# ---------- 2. system 消息：给模型设定角色/规则 ----------
print("\n=== 2. system 设定角色 ===")
review_messages = [
    {"role": "system", "content": "你是一个严苛的代码审查员，只指出问题，不说废话，最多说两点。"},
    {"role": "user", "content": "审查这段代码: users = []; users.append(input())"},
]
print(chat(review_messages))

# ---------- 3. 多轮对话：把历史消息全部带上 ----------
print("\n=== 3. 多轮对话（模型没有记忆，靠你每次带上历史）===")
history = [
    {"role": "user", "content": "我叫小明"},
    {"role": "assistant", "content": "你好小明！很高兴认识你。"},
    {"role": "user", "content": "我叫什么名字？"},  # 不带历史的话模型根本不知道
]
print(chat(history))

# ---------- 4. temperature 对比 ----------
print("\n=== 4. temperature 对比（同一个问题问两次）===")
q = [{"role": "user", "content": "给一只猫起个名字，只回答名字"}]
print(f"temperature=0:   {chat(q, temperature=0)}")
print(f"temperature=1.2: {chat(q, temperature=1.2)}")

def translate(text: str,temperature=0.5) -> str:
    """把中文翻译成英文"""
    messages = [
    {"role": "system", "content": "把输入翻译成英文"},
    {"role": "user", "content": text},
  ]
    return chat(messages, temperature=temperature)

print("temperature=0:"+ translate("tem我今天学了后端开发",temperature=0))
print("temperature=1:"+ translate("我今天学了后端开发",temperature=1))

def summarize(text:str) -> str:
    """用不超过20个字总结"""
    messages = [
    {"role": "system", "content": "用不超过20个字总结"},
    {"role": "user", "content": text},
  ]
    return chat(messages)

print(summarize("Flutter 是一个开源的移动应用开发框架，由 Google 开发。"))

# ========== ✏️ 课后练习 ==========
# 1. 写一个函数 translate(text)，用 system 设定"把输入翻译成英文"，测试"我今天学了后端开发"
# 2. 写一个函数 summarize(text)，要求模型"用不超过20个字总结"，总结一段你自己的 Flutter 项目介绍
# 3. 试试把 temperature 设为 0 问第1题的翻译，再设为 1 问一次，观察差异
# 4. （思考）为什么第 3 部分要把历史消息全发一遍？注释在代码里
