"""
第 27 课：ReAct 模式 —— Thought → Action → Observation 循环
运行方式：.venv/bin/python 27_react.py（需 Ollama 运行 qwen2.5:3b）

与第 8 课的区别：不依赖模型的原生 tool_calls，
而是用【提示词约定输出格式】+【正则解析】驱动工具调用——任何模型都能跑。
"""
import json
import re
import urllib.request

MODEL = "qwen2.5:3b"

# ---------- 工具注册表 ----------
KNOWLEDGE = {
    "sigenstor": "SigenStor 储能系统的容量是 48.06 度电（kWh）",
    "逆变器": "SigenStack 逆变器最大转换效率为 98.2%",
}

def search(query: str) -> str:
    for k, v in KNOWLEDGE.items():
        if k.lower() in query.lower():  # 大小写归一
            return v
    return "未找到相关信息"

def calculate(expr: str) -> str:
    try:
        return str(eval(expr))
    except Exception as e:
        return f"计算错误: {e}"

TOOLS = {"search": search, "calculate": calculate}

# ---------- ReAct 提示词：约定输出协议 ----------
SYSTEM = """你是一个会使用工具的助手。回答问题时，严格按以下格式输出：

Thought: （思考下一步该做什么）
Action: 工具名(参数)

系统会返回 Observation: 工具结果。你可以多次使用工具。信息足够后输出：

Thought: （总结思考）
Final Answer: 最终答案

可用工具：
- search(关键词)：查询知识库
- calculate(数学表达式)：计算

示例：
用户: 苹果多少钱？乘以2呢？
Thought: 我需要先查苹果价格
Action: search(苹果价格)
Observation: 苹果5元一斤
Thought: 价格是5元，计算5*2
Action: calculate(5*2)
Observation: 10
Thought: 已有答案
Final Answer: 苹果5元一斤，乘以2是10元"""

def chat(messages: list) -> str:
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps({
            "model": MODEL, "messages": messages, "stream": False,
            "options": {"temperature": 0, "stop": ["Observation:"]}  # 禁止模型自造观察
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read())["message"]["content"]

def react(question: str, max_loops: int = 5) -> str:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    for i in range(max_loops):
        output = chat(messages)
        # 双保险：若模型还是生成了 Observation，截断到它之前
        if "Observation:" in output:
            output = output[:output.index("Observation:")].rstrip()
        messages.append({"role": "assistant", "content": output})
        print(f"--- 第{i+1}轮 ---\n{output}\n")

        if "Final Answer:" in output:
            return output.split("Final Answer:")[-1].strip()

        # 解析 Action: 工具名(参数)
        m = re.search(r"Action:\s*(\w+)\((.+?)\)", output)
        if not m:
            return f"（模型未按格式输出，循环终止）\n{output}"
        tool_name, arg = m.group(1), m.group(2).strip('"\'')
        result = TOOLS.get(tool_name, lambda x: "未知工具")(arg)
        print(f"⚙️ 执行 {tool_name}({arg}) → {result}\n")
        messages.append({"role": "user", "content": f"Observation: {result}"})
    return "（达到最大轮数）"

if __name__ == "__main__":
    answer = react("SigenStor 的容量是多少度电？三台的容量加起来是多少？")
    print(f"🎯 最终答案: {answer}")

# ========== ✏️ 练习 ==========
# 1. 在 KNOWLEDGE 里加两条你自己的知识，提问需要【两次工具调用】的问题
# 2. 给 react() 加防护：模型输出了不存在的工具时，把"工具不存在，可用工具是..."
#    作为 Observation 反馈给模型让它自我纠正（而不是直接用默认 lambda 糊弄）
