"""
第 9 课：SSE 流式聊天后端 —— 打字机效果的秘密
启动方式：.venv/bin/uvicorn 09_chat_stream:app --port 8000
测试：curl -N -X POST http://127.0.0.1:8000/chat/stream -H "Content-Type: application/json" -d '{"message":"讲个短故事"}'

SSE（Server-Sent Events）概念：
  普通 HTTP：服务器攒完整段话，一次性返回
  SSE：服务器边生成边推送，响应是 text/event-stream，格式为 "data: {...}\\n\\n" 一条接一条
  Ollama 原生流式是 NDJSON（每行一个 JSON），我们把它"转译"成前端友好的 SSE
"""
import json
import urllib.request
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5:3b"

app = FastAPI(title="流式聊天后端")

# CORS：允许 Flutter Web 等浏览器来源访问（浏览器安全策略，macOS 桌面版不需要但加上无害）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: dict[str, list[dict]] = {}
SYSTEM_PROMPT = {"role": "system", "content": "你是一个友善、简洁的助手。"}

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

def sse(data: dict) -> str:
    """把 dict 打包成一条 SSE 消息"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    sid = req.session_id or uuid.uuid4().hex
    history = sessions.setdefault(sid, [SYSTEM_PROMPT])
    history.append({"role": "user", "content": req.message})

    def generate():
        # 第一条：先告诉前端 session_id（新会话时前端还不知道）
        yield sse({"type": "session", "session_id": sid})

        payload = {"model": MODEL, "messages": history, "stream": True}  # ← 开启流式
        ollama_req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        full_reply = []
        with urllib.request.urlopen(ollama_req, timeout=180) as resp:
            for line in resp:  # 一行一行读，而不是等全部生成完
                chunk = json.loads(line)
                token = chunk["message"].get("content", "")
                if token:
                    full_reply.append(token)
                    yield sse({"type": "token", "content": token})  # 立刻推给前端
                if chunk.get("done"):
                    break

        reply = "".join(full_reply)
        history.append({"role": "assistant", "content": reply})  # 完整回复存进记忆
        yield sse({"type": "done", "reply": reply})

    # StreamingResponse = FastAPI 的流式响应，media_type 声明这是 SSE
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/sessions")
def list_sessions():
    return {sid: f"{len(msgs)} 条消息" for sid, msgs in sessions.items()}
