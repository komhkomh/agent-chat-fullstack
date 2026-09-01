"""
第 17 课：数据库进阶 —— JOIN / 索引 / 事务
运行方式：python3 17_db_advanced.py
"""
import sqlite3
import time

conn = sqlite3.connect(":memory:")  # 内存数据库，跑完即焚，适合实验
conn.row_factory = sqlite3.Row
c = conn.cursor()

# ============================================================
# 第一部分：JOIN —— 把两张表"拼"起来查
# ============================================================
print("=" * 50)
print("第一部分：JOIN")
print("=" * 50)

c.executescript("""
    CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
    CREATE TABLE posts (
        id INTEGER PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),  -- 外键：指向 users.id
        title TEXT,
        views INTEGER
    );
    INSERT INTO users VALUES (1, '小明'), (2, '小红'), (3, '老王');
    INSERT INTO posts (user_id, title, views) VALUES
        (1, 'Flutter 入门', 100),
        (1, 'Agent 实战', 250),
        (2, '后端学习路线', 80);
    -- 注意：老王没有发过帖子
""")

# INNER JOIN：只保留"两边都配得上"的行（老王的帖子不存在 → 老王不出现）
print("\n① INNER JOIN：帖子 + 作者名")
rows = c.execute("""
    SELECT posts.title, users.name AS author, posts.views
    FROM posts
    JOIN users ON posts.user_id = users.id
""").fetchall()
for r in rows:
    print(f"   《{r['title']}》 作者:{r['author']} 阅读量:{r['views']}")

# LEFT JOIN：以左表为主，右边配不上就填 NULL（老王也出现，但统计是0）
print("\n② LEFT JOIN + 聚合：每个用户的发帖数（含没发过帖的老王）")
rows = c.execute("""
    SELECT users.name, COUNT(posts.id) AS post_count
    FROM users
    LEFT JOIN posts ON posts.user_id = users.id
    GROUP BY users.id
""").fetchall()
for r in rows:
    print(f"   {r['name']}: {r['post_count']} 篇")

# ============================================================
# 第二部分：索引 —— 从"翻遍全书"到"查目录"
# ============================================================
print("\n" + "=" * 50)
print("第二部分：索引")
print("=" * 50)

c.execute("CREATE TABLE big_users (id INTEGER PRIMARY KEY, email TEXT, age INTEGER)")
print("\n插入 10 万条数据……", end=" ", flush=True)
c.executemany(
    "INSERT INTO big_users (email, age) VALUES (?, ?)",
    [(f"user{i}@test.com", i % 80) for i in range(100_000)],
)
conn.commit()
print("完成")

# 没有索引时查一次
t0 = time.perf_counter()
c.execute("SELECT * FROM big_users WHERE email = 'user99999@test.com'").fetchone()
t_no_index = (time.perf_counter() - t0) * 1000
plan1 = c.execute("EXPLAIN QUERY PLAN SELECT * FROM big_users WHERE email = 'user99999@test.com'").fetchone()[3]
print(f"\n① 无索引查询: {t_no_index:.1f} ms")
print(f"   执行计划: {plan1}   ← SCAN = 全表扫描，10万行全翻一遍")

# 建索引后再查
c.execute("CREATE INDEX idx_email ON big_users(email)")
t0 = time.perf_counter()
c.execute("SELECT * FROM big_users WHERE email = 'user99999@test.com'").fetchone()
t_with_index = (time.perf_counter() - t0) * 1000
plan2 = c.execute("EXPLAIN QUERY PLAN SELECT * FROM big_users WHERE email = 'user99999@test.com'").fetchone()[3]
print(f"\n② 有索引查询: {t_with_index:.2f} ms（快了 {t_no_index/max(t_with_index,0.001):.0f} 倍）")
print(f"   执行计划: {plan2}   ← SEARCH = 查'目录'直达")

# ============================================================
# 第三部分：事务 —— 转账的"要么全成，要么全不成"
# ============================================================
print("\n" + "=" * 50)
print("第三部分：事务")
print("=" * 50)

c.executescript("""
    CREATE TABLE accounts (name TEXT PRIMARY KEY, balance INTEGER);
    INSERT INTO accounts VALUES ('小明', 100), ('小红', 0);
""")

def transfer(sender, receiver, amount, fail_midway=False):
    """转账：要么两步都成功，要么全撤销"""
    try:
        c.execute("BEGIN")  # 开启事务
        c.execute("UPDATE accounts SET balance = balance - ? WHERE name = ?", (amount, sender))
        if fail_midway:
            raise RuntimeError("模拟：扣款后系统崩了！")
        c.execute("UPDATE accounts SET balance = balance + ? WHERE name = ?", (amount, receiver))
        conn.commit()
        print(f"   ✅ 转账成功")
    except Exception as e:
        conn.rollback()  # 撤销本事务的所有改动
        print(f"   ❌ {e} → 已回滚（钱没动）")

print("\n① 正常转账 30 元:")
transfer('小明', '小红', 30)
print("   余额:", dict(c.execute("SELECT name, balance FROM accounts").fetchall()))

print("\n② 中途崩溃的转账 50 元:")
transfer('小明', '小红', 50, fail_midway=True)
print("   余额:", dict(c.execute("SELECT name, balance FROM accounts").fetchall()),
      "← 小明没少钱，小红没多钱，没有灵异事件 ✅")

conn.close()

# ========== ✏️ 练习 ==========
# 1. 给 posts 表写一条 JOIN：查出"阅读量超过90的帖子及其作者"
# 2. 在 tokens 表（15课）上，应该给哪一列建索引？为什么？（注释回答）
# 3. 思考：索引这么香，给所有列都建上行不行？有什么代价？（注释回答）
