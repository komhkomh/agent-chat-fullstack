"""
第 19 课：异步并发 —— 一个服务员怎么同时照看十桌客人
运行方式：python3 19_async.py

核心矛盾：I/O 等待（网络/数据库/磁盘）时，CPU 其实在"干等"
同步：干等     异步：等的时候先去干别的，好了叫我
"""
import asyncio
import time

# ---------- 模拟一次"慢 I/O 操作"（比如调 LLM API，要1秒）----------
def io_task_sync(name: str):
    time.sleep(1)  # 同步等待：整个线程被冻住1秒
    return f"{name} 完成"

async def io_task_async(name: str):
    await asyncio.sleep(1)  # 异步等待：冻结的是【这个任务】，不是线程
    return f"{name} 完成"

# ============================================================
# 第①幕：同步执行 3 个任务 → 排队干等
# ============================================================
print("① 同步：3 个任务排队执行")
t0 = time.perf_counter()
for i in range(1, 4):
    io_task_sync(f"任务{i}")
print(f"   总耗时: {time.perf_counter() - t0:.1f} 秒（1+1+1，秒秒都在干等）\n")

# ============================================================
# 第②幕：异步并发 3 个任务 → 等待时间重叠
# ============================================================
async def main_concurrent():
    # gather = 把多个任务【同时】挂上，一起等
    return await asyncio.gather(*[io_task_async(f"任务{i}") for i in range(1, 4)])

print("② 异步：3 个任务并发执行")
t0 = time.perf_counter()
asyncio.run(main_concurrent())
print(f"   总耗时: {time.perf_counter() - t0:.1f} 秒（等待重叠了，≈1秒！）\n")

# ============================================================
# 第③幕：陷阱！在 async 里用同步阻塞调用 → 异步失效
# ============================================================
async def fake_async_task(name: str):
    time.sleep(1)  # ❌ 在协程里用 time.sleep：把整个事件循环都冻住了！
    return f"{name} 完成"

async def main_fake():
    return await asyncio.gather(*[fake_async_task(f"任务{i}") for i in range(1, 4)])

print("③ 陷阱：async 函数里写了同步阻塞调用")
t0 = time.perf_counter()
asyncio.run(main_fake())
print(f"   总耗时: {time.perf_counter() - t0:.1f} 秒（又变回3秒了！异步白写）\n")

# ========== 关键概念（注释总结）==========
# async def  → 定义"协程"：一个可以暂停的任务
# await      → "我要等一个慢操作"：暂停本任务，把线程让给别人
# 事件循环    → 调度员：哪个任务的数据到了就唤醒哪个（一个线程服务所有任务）
# asyncio.gather → 同时发起多个任务
#
# 什么时候有用：I/O 密集（网络请求、DB查询、读写文件）
# 什么时候没用：CPU 密集（图像处理、大量计算）→ 那需要多进程
