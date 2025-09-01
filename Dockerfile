FROM python:3.11-slim
WORKDIR /app
COPY main.py /app/
COPY config.yml /app/

# 安装编译依赖，再安装 Python 包
RUN apt-get update && apt-get install -y \
        build-essential \
        libffi-dev \
        libssl-dev \
        python3-dev \
    && pip install --no-cache-dir telethon==1.35.1 pyyaml pytz \
    && apt-get remove -y build-essential python3-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

VOLUME ["/app/config.yml"]
CMD ["python", "main.py"]
