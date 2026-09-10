FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# 整个目录拷为 Python 包（Dockerfile 注释必须单独成行！）
COPY . ./server_v2/
EXPOSE 8020
CMD ["uvicorn", "server_v2.app:app", "--host", "0.0.0.0", "--port", "8020"]
