"""
第 7 课：MCP Server —— 把工具做成"标准化服务"
对比第 6 课：不再手写 TOOLS schema、不再手写 TOOL_FUNCTIONS 分发
装饰器 @mcp.tool() 会自动生成工具描述（函数名 + docstring + 类型标注）
运行方式：作为独立进程被 MCP 客户端启动（stdio 模式）
"""
import json
import math
import sqlite3
import urllib.request
from datetime import datetime

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("learn-python-tools")  # 给这个工具服务起个名

# ========== RAG 知识库（第 10 课的检索逻辑搬进服务端）==========
DOCUMENTS = [
    "小明的猫叫旺财，是一只三岁的橘猫，特别爱吃三文鱼。",
    "小明是一名 Flutter 开发者，2025 年开始学习后端和 AI。",
    "agent-chat-fullstack 是小明的毕业项目，技术栈是 Flutter + FastAPI + Ollama。",
    "Sigenergy 的储能产品支持远程监控，通过 MQTT 协议上报数据。",
    "小明最喜欢的城市是杭州，因为那里有西湖和他的第一份工作。",
]

def _embed(text: str) -> list[float]:
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/embeddings",
        data=json.dumps({"model": "nomic-embed-text", "prompt": text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["embedding"]

def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))

# 服务启动时把知识库向量化（真实项目用向量数据库持久化）
_VECTOR_STORE: list[tuple[str, list[float]]] | None = None

def _get_store():
    global _VECTOR_STORE
    if _VECTOR_STORE is None:
        _VECTOR_STORE = [(doc, _embed(doc)) for doc in DOCUMENTS]
    return _VECTOR_STORE

@mcp.tool()
def search_knowledge(question: str) -> str:
    """在私人知识库中检索信息（关于小明、他的猫、他的项目、Sigenergy 产品等）

    Args:
        question: 要检索的问题
    """
    q_vec = _embed(question)
    scored = [(doc, _cosine(q_vec, vec)) for doc, vec in _get_store()]
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:2]
    return "检索到相关资料：\n" + "\n".join(f"- {doc}" for doc, _ in top)

@mcp.tool()
def get_current_time() -> str:
    """获取当前的日期和时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@mcp.tool()
def query_user(name: str) -> str:
    """根据姓名查询数据库中的用户信息

    Args:
        name: 要查询的用户姓名
    """
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM users WHERE name = ?", (name,)).fetchone()
    conn.close()
    if row is None:
        return f"数据库里没有叫 {name} 的用户"
    return f"找到用户: id={row['id']}, 名字={row['name']}, 角色={row['role']}"

@mcp.tool()
def calculate(a: float, b: float, op: str) -> str:
    """做加减乘除"""
    if op == "+":
        return str(a + b)
    elif op == "-":
        return str(a - b)
    elif op == "*":
        return str(a * b)
    elif op == "/":
        if b == 0:
            return "除数不能为零"
        return str(a / b)
    else:
        return f"不支持的运算符: {op}"

@mcp.tool()
def count_users() -> str:
    """返回数据库用户总数"""
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return f"数据库中共有 {count} 个用户"

if __name__ == "__main__":
    mcp.run()  # 默认 stdio：通过标准输入输出和客户端通信（本课详解）
