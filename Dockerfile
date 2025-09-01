FROM python:3.11

WORKDIR /app
COPY main.py /app/
COPY config.yml /app/

# 安装依赖（容器启动时执行，避免 build 失败）
CMD ["sh", "-c", "python -m pip install --upgrade pip && pip install --no-cache-dir telethon==1.35.1 pyyaml pytz && python main.py"]
