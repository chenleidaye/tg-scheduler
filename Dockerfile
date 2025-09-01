FROM python:3.11-slim

WORKDIR /app
COPY main.py /app/
COPY config.yml /app/

# 更新 apt 并安装依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libssl-dev \
        python3-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 库
RUN pip install --no-cache-dir telethon==1.35.1 pyyaml pytz

VOLUME ["/app/config.yml"]
CMD ["python", "main.py"]
