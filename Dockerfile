# 使用官方 Python 镜像
FROM python:3.11-slim

WORKDIR /app

# 复制应用
COPY main.py /app/
COPY config.yml /app/
COPY requirements.txt /app/

# 安装依赖
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

VOLUME ["/app/config.yml", "/app/me_session.session"]

CMD ["python", "main.py"]
