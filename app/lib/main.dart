/// 毕业设计：Agent Chat —— Flutter 前端 + FastAPI/SSE 后端 + Ollama 本地大模型
///
/// 核心知识点：
/// 1. SSE 客户端：不用普通 http.get（一次性响应），而用 http.Client().send
///    拿到"流式响应"，逐行解析 "data: {...}" 事件
/// 2. 流式 UI：每收到一个 token 就 setState 追加到 AI 消息上 → 打字机效果
/// 3. session_id：第一轮由后端生成并下发，之后每次请求带上 → 多轮对话有记忆
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

const kBackendUrl = 'http://127.0.0.1:8000/chat/stream';

void main() => runApp(const AgentChatApp());

class AgentChatApp extends StatelessWidget {
  const AgentChatApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Agent Chat',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal),
        useMaterial3: true,
      ),
      home: const ChatPage(),
    );
  }
}

/// 一条聊天消息
class ChatMessage {
  ChatMessage({required this.isUser, required this.text});
  final bool isUser;
  String text; // 可变：AI 消息会被流式 token 不断追加
}

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  final _messages = <ChatMessage>[];
  final _inputController = TextEditingController();
  final _scrollController = ScrollController();
  final _httpClient = http.Client();

  String? _sessionId; // 后端发的"会话身份证"，实现多轮记忆
  bool _isStreaming = false; // 正在接收流式回复时禁止重复发送

  @override
  void dispose() {
    _inputController.dispose();
    _scrollController.dispose();
    _httpClient.close();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _inputController.text.trim();
    if (text.isEmpty || _isStreaming) return;

    setState(() {
      _messages.add(ChatMessage(isUser: true, text: text));
      _messages.add(ChatMessage(isUser: false, text: '')); // 占位，等 token 填充
      _isStreaming = true;
    });
    _inputController.clear();
    _scrollToBottom();

    // ---------- SSE 客户端核心 ----------
    final request = http.Request('POST', Uri.parse(kBackendUrl))
      ..headers['Content-Type'] = 'application/json'
      ..body = jsonEncode({'message': text, 'session_id': _sessionId});

    try {
      // client.send 拿到的是"还在传输中"的响应，body 是 Stream
      final response = await _httpClient.send(request);

      // 字节流 → 字符串流 → 按行切分（SSE 协议就是一行一条）
      await for (final line in response.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter())) {
        if (!line.startsWith('data: ')) continue; // 空行/其他行跳过
        final data = jsonDecode(line.substring(6)) as Map<String, dynamic>;

        switch (data['type']) {
          case 'session': // 第一条事件：后端下发 session_id
            _sessionId = data['session_id'] as String;
          case 'token': // 持续事件：追加一个字/词 → 打字机效果
            setState(() => _messages.last.text += data['content'] as String);
            _scrollToBottom();
          case 'done': // 结束事件
            break;
        }
      }
    } catch (e) {
      setState(() => _messages.last.text =
          '❌ 出错了：$e\n\n请确认后端已启动：\n.venv/bin/uvicorn 09_chat_stream:app --port 8000');
    } finally {
      setState(() => _isStreaming = false);
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Agent Chat · 本地 qwen2.5'),
        actions: [
          // 新会话按钮：清空界面 + 扔掉 session_id
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: '新会话',
            onPressed: () => setState(() {
              _messages.clear();
              _sessionId = null;
            }),
          ),
        ],
      ),
      body: Column(
        children: [
          // ---------- 消息列表 ----------
          Expanded(
            child: _messages.isEmpty
                ? const Center(
                    child: Text('开始聊天吧！后端：FastAPI + SSE，模型：本地 Ollama'))
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(12),
                    itemCount: _messages.length,
                    itemBuilder: (context, i) =>
                        _MessageBubble(message: _messages[i]),
                  ),
          ),
          // ---------- 输入区 ----------
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _inputController,
                      decoration: const InputDecoration(
                        hintText: '输入消息…',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                      onSubmitted: (_) => _send(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    onPressed: _isStreaming ? null : _send,
                    child: _isStreaming
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('发送'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// 聊天气泡：用户靠右，AI 靠左
class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message});
  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Align(
      alignment: message.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints: const BoxConstraints(maxWidth: 560),
        decoration: BoxDecoration(
          color: message.isUser
              ? scheme.primaryContainer
              : scheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(16),
        ),
        child: message.text.isEmpty && !message.isUser
            ? const Text('▍思考中…', style: TextStyle(color: Colors.grey))
            : Text(message.text),
      ),
    );
  }
}
