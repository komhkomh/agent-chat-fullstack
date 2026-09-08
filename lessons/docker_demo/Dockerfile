# ---- 第 21 课：Dockerfile —— 集装箱的"打包说明书" ----
# ① 底座：从一个现成的 Python 环境开始（不用从零装系统）
FROM python:3.13-slim

# ② 容器里的工作目录（相当于 cd /app）
WORKDIR /app

# ③ 先只拷贝依赖清单 → 装依赖（利用 Docker 层缓存，下面详解）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ④ 再拷贝应用代码
COPY app.py .

# ⑤ 声明端口（文档作用）+ 启动命令
EXPOSE 8010
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8010"]
#                             ↑ 必须 0.0.0.0！容器里监听 127.0.0.1 外面够不着
