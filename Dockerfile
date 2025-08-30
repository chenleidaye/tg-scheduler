FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 设置默认环境变量（可在 docker run 时覆盖）
ENV TG_API_ID=0
ENV TG_API_HASH=""

CMD ["python", "main.py"]
