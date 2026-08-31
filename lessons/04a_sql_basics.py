"""
第 4 课 A：SQL 基础 —— 用 sqlite3 直接操作数据库
运行方式：python3 04a_sql_basics.py
（会在当前目录生成 app.db 文件，那就是数据库本体）
"""
import sqlite3

# ---------- 1. 连接数据库（文件不存在会自动创建）----------
conn = sqlite3.connect("app.db")
conn.row_factory = sqlite3.Row  # 让查询结果可以像 dict 一样按列名取值
cursor = conn.cursor()

# ---------- 2. 建表（CREATE TABLE）----------
# 类似定义 Dart 的 class，但要声明每列的类型
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,  -- 主键：每行的唯一身份证，自动+1
        name  TEXT NOT NULL,                       -- NOT NULL：必填
        role  TEXT DEFAULT 'dev'                   -- DEFAULT：不填时的默认值
    )
""")
# 先清空，保证每次运行结果一致（学习专用，生产环境别这么干！）
cursor.execute("DELETE FROM users")

# ---------- 3. 插入（INSERT）----------
# ⚠️ 重要：永远用 ? 占位符传值！
# 不要把变量拼进 SQL 字符串，否则会被"SQL 注入"攻击（黑客往你数据库里塞命令）
cursor.execute("INSERT INTO users (name, role) VALUES (?, ?)", ("小明", "dev"))
cursor.execute("INSERT INTO users (name, role) VALUES (?, ?)", ("小红", "admin"))
cursor.execute("INSERT INTO users (name) VALUES (?)", ("老王",))  # role 用默认值
conn.commit()  # 提交：写操作必须 commit 才会真正落盘

# ---------- 4. 查询（SELECT）----------
rows = cursor.execute("SELECT * FROM users").fetchall()  # * = 所有列
print("全部用户:")
for row in rows:
    print(f"  id={row['id']}  name={row['name']}  role={row['role']}")

# 带条件查询（WHERE）
devs = cursor.execute("SELECT * FROM users WHERE role = ?", ("dev",)).fetchall()
print(f"\nrole=dev 的用户: {[r['name'] for r in devs]}")

# 查单个
row = cursor.execute("SELECT * FROM users WHERE id = ?", (1,)).fetchone()
print(f"id=1 的用户: {row['name']}")

# ---------- 5. 更新（UPDATE）----------
cursor.execute("UPDATE users SET role = ? WHERE id = ?", ("admin", 3))
conn.commit()
row = cursor.execute("SELECT * FROM users WHERE id = 3").fetchone()
print(f"\n老王升级后: role={row['role']}")

# ---------- 6. 删除（DELETE）----------
cursor.execute("DELETE FROM users WHERE id = ?", (2,))
conn.commit()
count = cursor.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
print(f"删除小红后剩余: {count} 人")

conn.close()

# ========== ✏️ 课后练习 ==========
# 1. 给 users 表插入一个你自己，role 填 "learner"
# 2. 查询所有 role 是 "admin" 的用户并打印
# 3. 写一条 SQL：把 id=1 的用户名字改成 "小明同学"
# 4. （思考）为什么插入时用 (?, ?) 而不是 f-string 拼接？把答案注释在代码里
