"""
第 14 课：带事实核查的 critic —— Agent 工具化 + RAG + 多Agent 三家合体
运行方式：python3 14_fact_check_critic.py

升级点：critic 不再是"一次性 chat"，而是带 search_knowledge 工具的迷你 Agent，
        能在审稿时主动查知识库验证事实，在流水线内部拦截幻觉。
"""
import json
import math
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434"
CHAT_MODEL = "qwen2.5:3b"
EMBED_MODEL = "nomic-embed-text"

def _post(path, payload):
    req = urllib.request.Request(
        f"{OLLAMA_URL}{path}", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())

def chat(messages, temperature=0.7):
    payload = {"model": CHAT_MODEL, "messages": messages, "temperature": temperature, "stream": False}
    return _post("/api/chat", payload)["message"]["content"]

# ---------- RAG 知识库（同第 10 课）----------
DOCUMENTS = [
    "小明的猫叫旺财，是一只三岁的橘猫，特别爱吃三文鱼。",
    "小明是一名 Flutter 开发者，2025 年开始学习后端和 AI。",
    "agent-chat-fullstack 是小明的毕业项目，技术栈是 Flutter + FastAPI + Ollama。",
    "Sigenergy 的储能产品支持远程监控，通过 MQTT 协议上报数据。",
    "小明最喜欢的城市是杭州，因为那里有西湖和他的第一份工作。",
]

def _embed(text):
    return _post("/api/embeddings", {"model": EMBED_MODEL, "prompt": text})["embedding"]

def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))

print("📚 知识库向量化中……")
VECTOR_STORE = [(doc, _embed(doc)) for doc in DOCUMENTS]

def search_knowledge(question: str) -> str:
    q = _embed(question)
    scored = sorted(((doc, _cosine(q, v)) for doc, v in VECTOR_STORE),
                    key=lambda x: x[1], reverse=True)
    # demo 库小，top_k 给足 3 条，尽量不漏正确文档
    return "\n".join(f"- {doc}" for doc, _ in scored[:3])

# ---------- critic 的工具装备（第 6 课的手写 schema 模式）----------
TOOLS = [{
    "type": "function",
    "function": {
        "name": "search_knowledge",
        "description": "在私人知识库中核查事实（项目信息、技术栈、人物、产品等）",
        "parameters": {"type": "object",
            "properties": {"question": {"type": "string", "description": "要核查的问题"}},
            "required": ["question"]},
    },
}]
TOOL_FUNCTIONS = {"search_knowledge": search_knowledge}

# ---------- 升级版 critic：带工具的迷你 Agent ----------
def critic(draft: str) -> str:
    """审稿 Agent：可调用 search_knowledge 核查事实后再下结论"""
    messages = [
        {"role": "system", "content": (
            "你是严苛的审稿人，拥有 search_knowledge 工具。\n"
            "流程：1. 找出文案中的事实性声明（如技术栈、人名、数据）\n"
            "2. 对没有把握的事实，调用 search_knowledge 核查\n"
            "3. 全部属实回复 PASS；有错用一句话指出错误和正确事实。")},
        {"role": "user", "content": f"待审文案：\n{draft}"},
    ]
    for _ in range(4):
        payload = {"model": CHAT_MODEL, "messages": messages, "tools": TOOLS,
                   "stream": False, "temperature": 0}
        msg = _post("/api/chat", payload)["message"]
        if not msg.get("tool_calls"):
            return msg["content"]  # 终审结论
        messages.append(msg)
        for call in msg["tool_calls"]:
            fn, args = call["function"]["name"], call["function"]["arguments"]
            print(f"      🔍 critic 核查: {fn}({args})")
            result = TOOL_FUNCTIONS[fn](**args)
            print(f"         资料: {result[:80]}...")
            messages.append({"role": "tool", "name": fn, "content": result})
    return "PASS"  # 保险丝

# ---------- 期末考试：一篇故意写错的稿子，看 critic 抓不抓 ----------
print("\n===== 考试：故意投喂错误文案 =====")
bad_draft = "agent-chat-fullstack 是小明的项目，基于 React + Express 打造，他的狗叫旺财。"
print(f"📄 待审文案: {bad_draft}")
print(f"📋 审稿结论: {critic(bad_draft)}")

# ---------- 完整流水线（写手 + 核查型 critic）----------
def planner(topic):
    return chat([
        {"role": "system", "content": "你是内容策划。把主题拆成3个要点的大纲，每点一句话。"},
        {"role": "user", "content": f"主题：{topic}"}])

def writer(outline):
    return chat([
        {"role": "system", "content": "你是文案写手。根据大纲写一段100字左右的介绍，只输出正文。"},
        {"role": "user", "content": f"大纲：\n{outline}"}])

def run_pipeline(topic):
    print(f"\n===== 完整流水线: {topic} =====")
    outline = planner(topic)
    for r in range(1, 3):
        draft = writer(outline)
        print(f"\n✍️  第{r}轮初稿: {draft}")
        verdict = critic(draft)
        print(f"📋 审稿结论: {verdict}")
        if "PASS" in verdict.upper():
            print(f"\n🎉 终稿:\n{draft}")
            return
        outline = f"{outline}\n\n必须修正：{verdict}"
        print("   ↩️  退回修改……")
    print("⚠️ 两轮后输出最后一版")

run_pipeline("介绍小明的项目 agent-chat-fullstack 的技术亮点")

# ========== ✏️ 练习 ==========
# 1. 给 critic 再加一个工具 get_current_time，让它能核查"2025年"这类时间声明
# 2. 观察流水线：如果写手第一轮就写对了，critic 还会调工具吗？（应不该调）
