# 使用完整 Python 镜像
FROM python:3.11

WORKDIR /app
COPY main.py /app/
COPY config.yml /app/

# 安装依赖
RUN pip install --no-cache-dir telethon==1.35.1 pyyaml pytz

VOLUME ["/app/config.yml"]
CMD ["python", "main.py"]
