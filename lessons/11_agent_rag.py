"""
第 11 课：Agent + RAG 合体 —— 企业级 AI 应用的雏形
架构：模型决策用哪个"数据源"（数据库工具 or 知识库工具），自己检索、自己回答
注意：本文件和第 8 课的 Agent 循环【完全一样】——客户端零改动，能力却升级了！
运行方式：.venv/bin/python 11_agent_rag.py
"""
import asyncio
import json
import urllib.request

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5:3b"
MAX_ROUNDS = 5

def ask_model(messages: list[dict], tools: list[dict]) -> dict:
    payload = {"model": MODEL, "messages": messages, "tools": tools, "stream": False}
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())["message"]

async def run_agent(session: ClientSession, user_input: str, tools: list[dict]):
    print(f"\n👤 用户: {user_input}")
    messages = [{"role": "user", "content": user_input}]
    for round_num in range(1, MAX_ROUNDS + 1):
        msg = ask_model(messages, tools)
        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            print(f"✅ 最终回答: {msg['content']}")
            return
        messages.append(msg)
        for call in tool_calls:
            fn_name = call["function"]["name"]
            fn_args = call["function"]["arguments"]
            print(f"🔧 模型请求: {fn_name}({fn_args})")
            result = await session.call_tool(fn_name, fn_args)
            text = result.content[0].text
            print(f"   工具返回: {text[:80]}{'...' if len(text) > 80 else ''}")
            messages.append({"role": "tool", "name": fn_name, "content": text})
    print("⚠️ 达到最大轮数")

async def main():
    server = StdioServerParameters(
        command="/Volumes/ASMT/code/learn-python/.venv/bin/python",
        args=["07_mcp_server.py"],
        cwd="/Volumes/ASMT/code/learn-python",
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = await session.list_tools()
            tools = [
                {"type": "function", "function": {
                    "name": t.name, "description": t.description or "",
                    "parameters": t.inputSchema}}
                for t in mcp_tools.tools
            ]
            print(f"📦 工具清单: {[t['function']['name'] for t in tools]}")

            # 三类问题，考模型的"数据源选择能力"：
            await run_agent(session, "小明的猫叫什么名字？多大了？", tools)      # → 应选 search_knowledge
            await run_agent(session, "数据库里老王的角色是什么？", tools)         # → 应选 query_user
            await run_agent(session, "小明为什么喜欢杭州？", tools)              # → 应选 search_knowledge

asyncio.run(main())
