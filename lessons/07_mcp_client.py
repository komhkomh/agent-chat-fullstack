"""
第 7 课：MCP Client —— 连接你的工具服务
演示 MCP 客户端的三大操作：连接 → 发现工具 → 调用工具
运行方式：.venv/bin/python 07_mcp_client.py
"""
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # 声明"要连接的服务"：客户端会帮我们启动这个进程
    server = StdioServerParameters(
        command="/Volumes/ASMT/code/learn-python/.venv/bin/python",
        args=["07_mcp_server.py"],
        cwd="/Volumes/ASMT/code/learn-python",
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()  # 握手：协商协议版本、能力

            # ① 发现工具：客户端问服务"你都有啥工具？"
            tools = await session.list_tools()
            print("📦 发现工具:")
            for t in tools.tools:
                print(f"   - {t.name}: {t.description}")

            # ② 调用工具：格式和第 6 课模型给我们的 tool_calls 一模一样
            result = await session.call_tool("query_user", {"name": "老王"})
            print(f"\n🔧 query_user('老王') → {result.content[0].text}")

            result = await session.call_tool("get_current_time", {})
            print(f"🔧 get_current_time() → {result.content[0].text}")

            result = await session.call_tool("calculate", {"a": 12345, "b": 6789, "op": "*"})
            print(f"🔧 calculate(12345, 6789, '*') → {result.content[0].text}")

            result = await session.call_tool("count_users", {})
            print(f"🔧 count_users() → {result.content[0].text}")

asyncio.run(main())
