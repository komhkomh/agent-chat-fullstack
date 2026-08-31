"""
第 7 课：MCP Server —— 把工具做成"标准化服务"
对比第 6 课：不再手写 TOOLS schema、不再手写 TOOL_FUNCTIONS 分发
装饰器 @mcp.tool() 会自动生成工具描述（函数名 + docstring + 类型标注）
运行方式：作为独立进程被 MCP 客户端启动（stdio 模式）
"""
import sqlite3
from datetime import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("learn-python-tools")  # 给这个工具服务起个名

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
