"""
第 10 课：RAG —— 让模型"开卷考试"
运行方式：python3 10_rag.py

RAG 管线（本课逐步实现）：
  ① 知识库文档 → ② 切块(chunk) → ③ Embedding 向量化 → ④ 存向量库
  ⑤ 提问也向量化 → ⑥ 余弦相似度找 Top-K → ⑦ 检索结果拼进 prompt → ⑧ 生成回答
"""
import json
import math
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434"
CHAT_MODEL = "qwen2.5:3b"
EMBED_MODEL = "nomic-embed-text"

# ---------- ①② 知识库：假装这是"小明的私人笔记" ----------
# 真实项目里这里是几百篇文档切成的小块；demo 里每句话就是一个 chunk
DOCUMENTS = [
    "小明的猫叫旺财，是一只三岁的橘猫，特别爱吃三文鱼。",
    "小明是一名 Flutter 开发者，2025 年开始学习后端和 AI。",
    "agent-chat-fullstack 是小明的毕业项目，技术栈是 Flutter + FastAPI + Ollama。",
    "Sigenergy 的储能产品支持远程监控，通过 MQTT 协议上报数据。",
    "小明最喜欢的城市是杭州，因为那里有西湖和他的第一份工作。",
]

# ---------- 基础 HTTP 工具 ----------
def _post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{OLLAMA_URL}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())

# ---------- ③ Embedding：把一段文字变成一个向量（数字列表）----------
def embed(text: str) -> list[float]:
    """调用 embedding 模型，返回文本的向量表示"""
    return _post("/api/embeddings", {"model": EMBED_MODEL, "prompt": text})["embedding"]

# ---------- ⑥ 余弦相似度：两个向量"方向"有多像 ----------
def cosine_similarity(a: list[float], b: list[float]) -> float:
    """范围 -1~1，越接近 1 语义越相似。纯数学，不需要 AI"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b)

# ---------- ④ 建向量库（真实项目用 Chroma/pgvector，demo 用内存 list）----------
print("📚 正在把知识库向量化……")
VECTOR_STORE = [(doc, embed(doc)) for doc in DOCUMENTS]
print(f"   完成，{len(VECTOR_STORE)} 个文档块已入库\n")

# ---------- ⑤⑥⑦ 检索：找和问题最相关的文档块 ----------
def retrieve(question: str, top_k: int = 2) -> list[tuple[str, float]]:
    """返回最相关的 top_k 个文档块及其相似度"""
    q_vec = embed(question)
    scored = [(doc, cosine_similarity(q_vec, vec)) for doc, vec in VECTOR_STORE]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]

# ---------- ⑧ 生成：把检索结果塞进 prompt，让模型开卷答题 ----------
def rag_answer(question: str):
    print(f"👤 提问: {question}")

    # 检索
    hits = retrieve(question)
    print("🔍 检索到的资料:")
    for doc, score in hits:
        print(f"   [{score:.3f}] {doc}")

    # 把资料拼进 prompt——RAG 的"魔法"就这一步
    context = "\n".join(doc for doc, _ in hits)
    messages = [
        {"role": "system", "content": f"根据以下资料回答问题。资料里没有的信息，就说'资料中没有提到'，不要编造。\n\n【资料】\n{context}"},
        {"role": "user", "content": question},
    ]
    resp = _post("/api/chat", {"model": CHAT_MODEL, "messages": messages, "stream": False})
    print(f"✅ 回答: {resp['message']['content']}\n")

# ---------- 见证 ----------
# 这些问题模型本来不可能知道答案（全在"小明的私人笔记"里）
rag_answer("小明的猫叫什么名字？它爱吃什么？")
rag_answer("小明的毕业项目用了什么技术栈？")
rag_answer("小明的猫今年几岁了，是橘猫吗？")

# ========== ✏️ 课后练习 ==========
# 1. 加 3 条你自己的"私人笔记"到 DOCUMENTS，问模型相关内容
# 2. 把 top_k 改成 1 再跑，观察回答质量变化（体会"检索不全"的风险）
# 3. （思考）问一个资料里完全没有的问题（如"小明开什么车？"），
#    观察模型是否遵守"不编造"的指令。如果它还是编了，怎么改进？
