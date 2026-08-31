"""
第二课：JSON 与数据处理 —— 后端开发的日常
运行方式：python3 02_json_data.py
"""

import json  # Python 内置的 JSON 工具，不用安装

# ========== 1. dict ↔ JSON 字符串（后端最频繁的操作）==========
user = {"name": "小明", "age": 28, "skills": ["Flutter", "Python"]}

# dict → JSON 字符串（接口"返回数据"时做的事）
json_str = json.dumps(user, ensure_ascii=False)  # ensure_ascii=False 让中文正常显示
print(f"JSON 字符串: {json_str}")
print(f"类型: {type(json_str)}")  # <class 'str'>


# JSON 字符串 → dict（接口"接收数据"时做的事）
parsed = json.loads(json_str)
print(f"解析回来: {parsed['name']}, 类型: {type(parsed)}")

# ========== 2. 真实场景：处理一个"接口返回" ==========
# 假装这是从服务器拿到的用户列表（list 套 dict，后端最常见的数据结构）
api_response = """
[
    {"id": 1, "name": "小明", "role": "dev",   "active": true},
    {"id": 2, "name": "小红", "role": "admin", "active": true},
    {"id": 3, "name": "老王", "role": "dev",   "active": false}
]
"""
users = json.loads(api_response)
print(f"名字两个字的用户有: {[u['name'] for u in users if len(u['name']) == 2]}")  # 字符串长度

# 需求1：找出所有 active 的用户 → 列表推导式
active_users = [u for u in users if u["active"]]
print(f"\n活跃用户: {[u['name'] for u in active_users]}")

# 需求2：找出所有 dev → 同样的模式
devs = [u["name"] for u in users if u["role"] == "dev"]
print(f"开发者: {devs}")

# 需求3：按 id 查找用户 → 写一个可复用的函数
def find_user_by_id(users: list, user_id: int):
    for u in users:
        if u["id"] == user_id:
            return u
    return None  # 找不到返回 None（后端的常见约定）

found = find_user_by_id(users, 2)
print(f"找到 id=2 的用户: {found['name']}")

# ========== 3. 类型标注（type hints）—— 让 AI 和你都不犯错 ==========
# Python 不强制类型，但写上标注后：编辑器有提示、AI 生成代码更准、FastAPI 会用它自动校验
def create_greeting(name: str, age: int) -> str:
    return f"{name}，{age} 岁"

print(f"\n{create_greeting('小明', 28)}")

# ========== 4. 错误处理（接口不能一出错就崩）==========
bad_json = "{这不是合法JSON"
try:
    json.loads(bad_json)
except json.JSONDecodeError as e:
    print(f"\n解析失败，但要优雅地处理: {e}")
    # 真实后端里这里会返回 {"error": "请求格式不对"} + 状态码 400

def to_summary(users):
    return [{"label": f"{u['name']}({u['role']})"} for u in users]

# ========== ✏️ 课后练习 ==========
# 1. 从 users 里找出"名字是两个字"的用户（提示: len(u["name"]) == 2）
# 2. 写一个函数 to_summary(users)，返回这样的 list：
#    [{"label": "小明(dev)"}, {"label": "小红(admin)"}, ...]
#    提示: 列表推导式 + f-string 嵌套 dict
# 3. 给 find_user_by_id 加上类型标注（users 是 list，user_id 是 int）
