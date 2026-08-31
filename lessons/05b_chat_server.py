"""
第 5 课·下半场：FastAPI + LLM —— 你自己的 /chat 后端
启动方式：
    .venv/bin/uvicorn 05b_chat_server:app --reload
测试：http://127.0.0.1:8000/docs
"""
from contextlib import asynccontextmanager
import json
import urllib.request
import uuid
import sqlite3

from fastapi import FastAPI
from pydantic import BaseModel



DB_FILE = "app.db"  # 复用 04a 生成的数据库文件

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@asynccontextmanager
async def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE if NOT EXISTS sessions (
        id         TEXT PRIMARY KEY,     -- 会话 id（uuid）
        messages   TEXT NOT NULL,        -- 整个 messages 列表 json.dumps 后的字符串
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
""")
    conn.commit()
    conn.close()
    yield

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5:3b"

app = FastAPI(title="我的 AI 聊天后端", lifespan=init_db)

# ---------- 第 5 课的 chat 函数原样搬来 ----------
def chat(messages: list[dict]) -> str:
    """给 LLM 发一组消息，返回回复文本"""
    payload = {"model": MODEL, "messages": messages, "stream": False}
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())["message"]["content"]

# ---------- 记忆存储：session_id -> 该会话的历史消息 ----------
# 用 dict 存所有会话，每个会话有自己的历史（解决"模型无记忆"问题）
sessions: dict[str, list[dict]] = {}

SYSTEM_PROMPT = {"role": "system", "content": "你是一个友善、简洁的助手，回答不超过三句话。"}

PERSONAS = {
    "default": "你是一个友善、简洁的助手，回答不超过三句话。",
    "pirate":  "你是加勒比海盗船长，说话带' arrr '和航海黑话。",
    "poet":    "你是一位诗人，所有回答都用诗句。",
}

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None  # 不传 = 开新会话
    persona: str | None = None  # 可选的人设，比如传 "pirate" 就用"你是海盗船长"当 system prompt（新会话才生效）

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    turns: int  # 已经聊了几轮

# ---------- 核心接口 ----------
@app.post("/chat", response_model=ChatResponse)
def chat_api(req: ChatRequest):
    # 1. 没有 session_id 就开新会话（uuid 生成随机 id）
    sid = req.session_id or uuid.uuid4().hex
    # 2. 取该会话的历史；新会话则初始化（带上 system 规则）
    history = sessions.get(sid)
    conn = get_conn()
    cursor = conn.cursor()
    if history is None:
        row = cursor.execute("SELECT messages FROM sessions WHERE id = ?", (sid,)).fetchone()
        if row:
            history = json.loads(row["messages"])
        else:
            prompt = PERSONAS.get(req.persona or "default", PERSONAS["default"])
            history = [{"role": "system", "content": prompt}]
        sessions[sid] = history

    # 3. 用户的话追加进历史
    history.append({"role": "user", "content": req.message})
    # 4. 整个历史发给模型（注入记忆！）
    reply = chat(history)
    # 5. 模型的回复也存进历史，供下一轮使用
    history.append({"role": "assistant", "content": reply})
    cursor.execute("""
        INSERT INTO sessions (id, messages) VALUES (?, ?)
        ON CONFLICT(id) UPDATE messages SET messages = excluded.messages, updated_at = CURRENT_TIMESTAMP
    """, (sid, json.dumps(history)))
    conn.commit()
    conn.close()
    return ChatResponse(session_id=sid, reply=reply, turns=len(history) // 2)

@app.delete("/chat/{session_id}")
def clear_session(session_id: str):
    """清空某个会话的记忆"""
    sessions.pop(session_id, None)
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    return {"message": "记忆已清空"}

@app.get("/sessions")
def list_sessions():
    """看看当前内存里有几个会话、各聊了几条"""
    return {sid: f"{len(msgs)} 条消息" for sid, msgs in sessions.items()}

# ========== ✏️ 课后练习 ==========
# 1. 【记忆持久化】重启服务后 sessions 就丢了（和第3课 list 一样的毛病）。
#    用第 4 课的 SQLite 把每个会话的历史存进数据库
# （提示：messages 可以 json.dumps 后存 TEXT 列）
# 2. 【人设切换】给 ChatRequest 加一个可选的 persona 字段，
#    比如传 "pirate" 就用"你是海盗船长"当 system prompt（新会话才生效）
# 3. （思考）现在的记忆会无限增长，结合上一课的"上下文窗口"概念，
#    说说会出现什么问题？怎么解决？注释在代码里
