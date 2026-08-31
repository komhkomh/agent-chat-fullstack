"""
第 13 课：多 Agent 协作 —— 让 AI 组成团队
运行方式：python3 13_multi_agent.py

模式1（本课实现）：流水线（Sequential Pipeline）
  策划 → 写手 → 审稿 →（不满意则退回写手，最多2轮）→ 出品
模式2（了解）：主管（Supervisor）——你第8课的工具路由其实就是它的雏形
"""
import json
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5:3b"

def chat(messages: list[dict], temperature: float = 0.7) -> str:
    payload = {"model": MODEL, "messages": messages, "temperature": temperature, "stream": False}
    req = urllib.request.Request(
        OLLAMA_URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())["message"]["content"]

# ---------- 三个 Agent = 三个 system prompt ----------
# 每个"员工"就是一个函数：角色设定 + 接收上游输入 + 产出给下游
def planner(topic: str) -> str:
    """策划：把任务拆成大纲"""
    return chat([
        {"role": "system", "content": "你是内容策划。把主题拆成3个要点的大纲，每点一句话，只输出大纲。"},
        {"role": "user", "content": f"主题：{topic}"},
    ])

def writer(outline: str) -> str:
    """写手：按大纲成文"""
    return chat([
        {"role": "system", "content": "你是文案写手。根据大纲写一段100字左右的介绍，语言生动，只输出正文。"},
        {"role": "user", "content": f"大纲：\n{outline}"},
    ])

def critic(draft: str) -> str:
    """审稿：评审并给出 PASS 或修改意见"""
    return chat([
        {"role": "system", "content": "你是严苛的审稿人。评审文案：如果质量合格，只回复'PASS'；如果有问题，用一句话指出最关键的修改意见。"},
        {"role": "user", "content": f"文案：\n{draft}"},
    ], temperature=0)  # 审稿要稳定，温度调0

# ---------- 流水线编排（这就是"编排"本体：只是普通的流程控制代码）----------
def run_pipeline(topic: str):
    print(f"🎯 任务: {topic}\n")

    print("📋 [策划] 拆解大纲...")
    outline = planner(topic)
    print(f"   大纲:\n{outline}\n")

    for round_num in range(1, 3):  # 最多写2轮
        print(f"✍️  [写手] 第{round_num}轮创作...")
        draft = writer(outline)
        print(f"   初稿: {draft}\n")

        print("🔍 [审稿] 评审中...")
        verdict = critic(draft)
        print(f"   审稿意见: {verdict}\n")

        if "PASS" in verdict.upper():
            print(f"🎉 终稿:\n{draft}")
            return draft
        # 不通过：把审稿意见反馈给写手（类似工具结果回喂！）
        outline = f"{outline}\n\n注意改进：{verdict}"
        print("   ↩️  退回写手修改...\n")

    print("⚠️ 两轮后仍未过审，输出最后一版")
    return draft

run_pipeline("为开源项目 agent-chat-fullstack 写一句吸引开发者的项目介绍")

# ========== ✏️ 课后练习 ==========
# 1. 在流水线里加第4个Agent：translator（把终稿翻译成英文）
# 2. 把"最多2轮"改成"最多3轮"，观察质量是否提升
# 3. （思考）如果让 critic 也能调用 search_knowledge 核查事实，
#    这个流水线会变成什么样？画出新的流程（注释在代码里）
