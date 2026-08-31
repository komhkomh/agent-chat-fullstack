"""
第 8 课（毕业版）：真·Agent = 模型决策（Ollama）+ 工具执行（MCP）
对比：
  06 课：模型决策 + 手写工具分发（焊死）
  07 课：手写决策 + MCP 服务（没模型）
  08 课：模型决策 + MCP 服务（完整闭环）✅
运行方式：.venv/bin/python 08_agent_mcp.py
"""
import asyncio
import json
import urllib.request

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5:3b"
MAX_ROUNDS = 5  # 防死循环保险丝

# ---------- 决策者：问模型 ----------
def ask_model(messages: list[dict], tools: list[dict]) -> dict:
    """把对话历史+工具菜单发给模型，返回它的'决定'"""
    payload = {"model": MODEL, "messages": messages, "tools": tools, "stream": False}
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())["message"]

# ---------- 翻译官：MCP 工具描述 → Ollama 工具格式 ----------
def to_ollama_tools(mcp_tools) -> list[dict]:
    """MCP 的 inputSchema 本身就是 JSON Schema，直接映射即可——这就是标准化的红利"""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema,
            },
        }
        for t in mcp_tools.tools
    ]

# ---------- Agent 循环（和第 6 课几乎一样，只换了执行方式）----------
async def run_agent(session: ClientSession, user_input: str, tools: list[dict]):
    print(f"\n👤 用户: {user_input}")
    messages = [{"role": "user", "content": user_input}]

    for round_num in range(1, MAX_ROUNDS + 1):
        msg = ask_model(messages, tools)
        tool_calls = msg.get("tool_calls")

        if not tool_calls:  # 模型没有工具请求 = 最终回答
            print(f"✅ 最终回答: {msg['content']}")
            return

        messages.append(msg)
        for call in tool_calls:
            fn_name = call["function"]["name"]
            fn_args = call["function"]["arguments"]
            print(f"🔧 第{round_num}轮, 模型请求: {fn_name}({fn_args})")

            # 关键替换：06 课是 TOOL_FUNCTIONS[name](**args)
            #           08 课是经由 MCP 协议调用独立服务 ✅
            result = await session.call_tool(fn_name, fn_args)
            text = result.content[0].text
            print(f"   MCP 服务返回: {text}")
            messages.append({"role": "tool", "name": fn_name, "content": text})

    print("⚠️ 达到最大轮数，强制停止")

# ---------- 主流程 ----------
async def main():
    server = StdioServerParameters(
        command="/Volumes/ASMT/code/learn-python/.venv/bin/python",
        args=["07_mcp_server.py"],
        cwd="/Volumes/ASMT/code/learn-python",
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = to_ollama_tools(await session.list_tools())
            print(f"📦 从 MCP 服务发现 {len(tools)} 个工具，已交给模型")

            # 连问三题，覆盖：查时间、查数据库、算数
            await run_agent(session, "现在几点了？", tools)
            await run_agent(session, "数据库里有多少个用户？老王的角色是什么？", tools)
            await run_agent(session, "12345 乘以 6789 等于几？", tools)

asyncio.run(main())
