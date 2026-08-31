"""
第 6 课：Function Calling —— 让 AI 学会"用工具"
运行方式：python3 06_function_calling.py
"""
import json
import sqlite3
import urllib.request
from datetime import datetime

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5:3b"

# ---------- 第一步：工具本体（就是普通 Python 函数）----------
def get_current_time() -> str:
    """获取当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def query_user(name: str) -> str:
    """按名字查第 4 课的 users 表"""
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM users WHERE name = ?", (name,)).fetchone()
    conn.close()
    if row is None:
        return f"数据库里没有叫 {name} 的用户"
    return f"找到用户: id={row['id']}, 名字={row['name']}, 角色={row['role']}"

def count_users() -> str:
    """返回数据库用户总数"""
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return f"数据库中共有 {count} 个用户"

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

# 工具注册表：名字 → 函数对象（Agent 靠它分发调用）
TOOL_FUNCTIONS = {
    "get_current_time": get_current_time,
    "query_user": query_user,
    "count_users": count_users,
    "calculate": calculate,
}

# ---------- 第二步：用 JSON Schema 向模型"介绍"工具 ----------
# 模型看不到你的代码，只看得懂这份"说明书"——description 写得越清楚，模型用得越准
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前的日期和时间",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_user",
            "description": "根据姓名查询数据库中的用户信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "要查询的用户姓名"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_users",
            "description": "返回数据库中用户的总数",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行加减乘除运算",
            "parameters": {
                "type": "object",   

                "properties": {
                    "a": {"type": "number", "description": "第一个操作数"},
                    "b": {"type": "number", "description": "第二个操作数"},
                    "op": {"type": "string", "description": "运算符 (+, -, *, /)"}
                },
                "required": ["a", "b", "op"]
            }
        }
    }
]

def chat_with_tools(messages: list[dict]) -> dict:
    """带工具说明书调用模型，返回完整的 message 对象"""
    payload = {"model": MODEL, "messages": messages, "tools": TOOLS, "stream": False}
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())["message"]

# ---------- 第三步：Agent 循环（本课灵魂）----------
def run_agent(user_input: str):
    print(f"\n👤 用户: {user_input}")
    messages = [{"role": "user", "content": user_input}]

    for round_num in range(1, 6):  # 最多循环 5 轮，防死循环
        msg = chat_with_tools(messages)
        tool_calls = msg.get("tool_calls")

        # 情况 A：模型没想调工具 → 这就是最终回答，循环结束
        if not tool_calls:
            print(f"✅ 最终回答: {msg['content']}")
            return

        # 情况 B：模型请求调工具 → 我们执行，结果喂回去，继续循环
        messages.append(msg)  # 模型"想调工具"这条消息也要进历史
        for call in tool_calls:
            fn_name = call["function"]["name"]
            fn_args = call["function"]["arguments"]
            print(f"🔧 第{round_num}轮, 模型请求: {fn_name}({fn_args})")
            result = TOOL_FUNCTIONS[fn_name](**fn_args)  # 真正执行的是我们！
            print(f"   工具返回: {result}")
            messages.append({"role": "tool", "name": fn_name, "content": result})

    print("⚠️ 达到最大轮数，强制停止")

# ---------- 见证奇迹 ----------
run_agent("现在几点了？")
run_agent("数据库里老王的角色是什么？")
run_agent("1+1等于几？")  # 观察：不需要工具时，模型会直接回答
run_agent("数据库里有几个用户？")  # 观察：需要工具时，模型会请求调用
run_agent("12345 乘以 6789 等于几？")


# ========== ✏️ 课后练习 ==========
# 1. 加工具 count_users()：返回数据库用户总数，然后问"数据库里有几个用户？"
# 2. 加工具 calculate(a, b, op)：做加减乘除，问"12345 乘以 6789 等于几？"
#    体会：模型自己算数很烂，但它会"聪明地"请求工具来算
# 3. （思考）模型返回的 tool_calls 里 name 是字符串，我们是靠 TOOL_FUNCTIONS
#    字典分发执行的。如果模型"幻觉"出一个不存在的工具名，会发生什么？怎么防？
