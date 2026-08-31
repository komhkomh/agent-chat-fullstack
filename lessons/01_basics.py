"""
第一课：Python 基础语法（Dart 开发者对照版）
运行方式：python3 01_basics.py
"""

# ========== 1. 变量与 f-string ==========
name = "小明"
age = 28
print(f"你好，我是 {name}，今年 {age} 岁")  # 类似 Dart 的 "你好，我是 $name"

# ========== 2. list（类似 Dart 的 List）==========
skills = ["Flutter", "Dart", "UI"]
skills.append("Python")  # 类似 Dart 的 add()
print(f"技能列表: {skills}, 第一个: {skills[0]}, 数量: {len(skills)}")

# ========== 3. dict（类似 Dart 的 Map，也是 JSON 的原型）==========
user = {
    "name": "小明",
    "role": "developer",
    "skills": skills,
    "level": "beginner" 
}
print(f"用户名: {user}")  # 后端开发中 90% 的数据都是这种结构

# ========== 4. 函数 ==========
def greet(name, lang="Python"):  # 默认参数，类似 Dart 的 [lang = "Python"]
    return f"{name} 正在学 {lang}"

print(greet("小明"))
print(greet("小红", "Go"))

# ========== 5. 条件与循环（注意：缩进就是语法）==========
for skill in skills:
    if skill == "Python":
        print(f"  👉 正在学: {skill}")
    else:
        print(f"  ✅ 已会: {skill}")

# ========== 6. class（后端里常用来定义数据模型）==========
class Task:
    def __init__(self, title, done=False):  # __init__ 就是构造函数
        self.title = title  # self 类似 Dart 的 this，但必须显式写出
        self.done = done

    def complete(self):
        self.done = True
        return f"任务「{self.title}」已完成！"

task = Task("学会 Python 基础")
print(task.complete())

# ========== 7. 列表推导式（Python 特色，超常用）==========
# Dart:  skills.where((s) => s.length > 3).map((s) => s.toUpperCase()).toList()
upper_skills = [s.upper() for s in skills if len(s) > 3]
print(f"大写技能: {upper_skills}")

def level_up(user):
    user["level"] = "intermediate"
    
    return user
print(level_up(user))

skill_lengths = [len(s) for s in skills]
print(f"技能长度: {skill_lengths}")

# ========== ✏️ 课后练习 ==========
# 1. 给 user 字典加一个 "level" 字段，值为 "beginner"，然后打印整个字典
# 2. 写一个函数 level_up(user)，把 level 改成 "intermediate"
# 3. 用列表推导式，生成一个包含 skills 里每个技能名称长度的 list
#    提示: [len(???) for ??? in skills]
