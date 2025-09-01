# 使用完整 Python 镜像，避免依赖问题
FROM python:3.11

WORKDIR /app

# 拷贝源码和配置文件
COPY main.py /app/
COPY config.yml /app/

# 升级 pip 并使用国内镜像安装依赖
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
        telethon==1.35.1 \
        pyyaml \
        pytz

# 挂载 config 文件
VOLUME ["/app/config.yml"]

# 默认启动脚本
CMD ["python", "main.py"]
