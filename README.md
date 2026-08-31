# Agent Chat · 全栈本地 AI 聊天应用

一个**完全本地运行**的 AI 聊天应用：Flutter 桌面端 + FastAPI 流式后端 + Ollama 本地大模型。
从零手写，不依赖任何云端 API——数据不出本机。

![架构](https://img.shields.io/badge/架构-Flutter%20%2B%20FastAPI%20%2B%20Ollama-teal)

## ✨ 功能

- 💬 多轮对话（session_id 会话记忆）
- ⌨️ SSE 流式输出（打字机效果）
- 🧠 本地大模型（qwen2.5:3b via Ollama）
- 🔧 可扩展 MCP 工具调用（见 `lessons/07-08`）

## 🏗 架构

```
┌─────────────┐   SSE (text/event-stream)   ┌──────────────┐   HTTP   ┌─────────────┐
│  Flutter    │ ───────────────────────────▶ │   FastAPI    │ ───────▶ │   Ollama    │
│  macOS App  │ ◀─────────────────────────── │  (Python)    │ ◀─────── │  qwen2.5:3b │
└─────────────┘      token 逐字推送           └──────────────┘  NDJSON  └─────────────┘
     app/                  server/09_chat_stream.py                 本地模型
```

## 📂 目录结构

```
agent-chat-fullstack/
├── app/        # Flutter 桌面应用（macOS）
├── server/     # FastAPI 流式聊天后端
└── lessons/    # 学习路径：Python → FastAPI → 数据库 → LLM → Agent → MCP（11 个可运行课件）
```

## 🚀 快速开始

### 0. 前置：安装并启动 Ollama

```bash
brew install ollama
ollama serve &          # 启动服务
ollama pull qwen2.5:3b  # 下载模型（约 2GB）
```

### 1. 启动后端

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn 09_chat_stream:app --port 8000
```

### 2. 启动 App

```bash
cd app
flutter pub get
flutter run -d macos
```

打开后输入消息，体验打字机效果的流式回复。

## 📚 lessons/ 学习路径

| 文件 | 主题 |
|---|---|
| 01-02 | Python 基础语法 / JSON 数据处理 |
| 03-04 | FastAPI 接口 / SQLite 数据库（含 SQL 注入防护） |
| 05 | LLM API 调用 / 消息结构 / 会话记忆持久化 |
| 06 | Function Calling（Agent 核心循环） |
| 07 | MCP Server & Client（工具标准化协议） |
| 08 | 完整 Agent：模型决策 + MCP 工具执行 |
| 09 | SSE 流式后端（本项目使用的服务） |

每个文件都是可直接运行的独立课件，含练习题。

## 🛠 技术栈

Flutter 3 · Dart · FastAPI · SQLite · Ollama · MCP SDK · SSE
