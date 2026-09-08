"""
第 22 课：ORM —— 用 Python 类操作数据库（SQLModel 版）
运行方式：python3 22_orm.py

ORM（Object-Relational Mapping，对象关系映射）：
  手写 SQL: "INSERT INTO users (name, role) VALUES ('小明', 'dev')"
  ORM:      session.add(User(name="小明", role="dev"))
  → 类 = 表，对象 = 行，属性 = 列。SQL 由框架替你生成。

SQLModel：FastAPI 作者出品，SQLAlchemy（ORM引擎）+ Pydantic（数据校验）合体
"""
from sqlmodel import Field, Session, SQLModel, create_engine, select

# ---------- ① 定义模型：一个类 = 一张表 ----------
class User(SQLModel, table=True):       # table=True = 这是张真表
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)       # index=True = 顺手建索引（第17课！）
    role: str = "dev"                   # 默认值

# ---------- ② 引擎 + 建表 ----------
engine = create_engine("sqlite:///orm_demo.db")  # engine = 数据库连接的管理者
SQLModel.metadata.create_all(engine)   # 自动生成 CREATE TABLE（模型变了还能迁移）

print("=== ③ 增（Create）：add + commit ===")
with Session(engine) as session:       # Session = 一次数据库对话（with 自动关闭）
    session.add(User(name="小明"))
    session.add(User(name="小红", role="admin"))
    session.add(User(name="老王"))
    session.commit()                   # 事务概念原样适用！

print("=== ④ 查（Read）：select 语句是 Python 表达式 ===")
with Session(engine) as session:
    # 手写 SQL: SELECT * FROM user WHERE role = 'dev'
    devs = session.exec(
        select(User).where(User.role == "dev")
    ).all()
    print(f"   dev 用户: {[u.name for u in devs]}")

    # 按主键查：一行搞定
    user = session.get(User, 1)
    print(f"   id=1: {user.name}")

print("=== ⑤ 改（Update）：改对象属性 → add → commit ===")
with Session(engine) as session:
    user = session.get(User, 3)
    user.role = "admin"                # 像改普通对象一样改
    session.add(user)
    session.commit()
    print(f"   老王新角色: {session.get(User, 3).role}")

print("=== ⑥ 删（Delete）===")
with Session(engine) as session:
    user = session.get(User, 2)
    session.delete(user)
    session.commit()
    print(f"   剩余: {[u.name for u in session.exec(select(User)).all()]}")

# ========== ✏️ 练习 ==========
# 1. 定义一张 Post 表（title: str, views: int, user_id: int = Field(foreign_key="user.id")）
#    插入几条数据，并用 select(Post).where(Post.views > 90) 查询
# 2. （思考）对比第 4 课手写 SQL 的版本，ORM 各有什么得失？
#    提示从"防注入、可维护性、复杂 JOIN 谁方便"三个角度想
