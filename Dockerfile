# 使用官方 Python 3.11 slim 版本
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY main.py config.yml requirements.txt /app/

# 安装系统依赖（编译部分 Python 包需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libssl-dev \
        python3-dev \
        wget \
        curl \
    && python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get remove -y build-essential python3-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# 挂载配置文件卷（可选）
VOLUME ["/app/config.yml", "/app/me_session.session"]

# 默认启动命令
CMD ["python", "main.py"]
