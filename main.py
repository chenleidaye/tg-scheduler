import asyncio
import yaml
import os
from datetime import datetime, timedelta
from telethon import TelegramClient
import traceback
import pytz

# ====== 时区 ======
tz = pytz.timezone("Asia/Shanghai")

# ====== 从环境变量读取 API 信息 ======
api_id = int(os.getenv("TG_API_ID", "0"))
api_hash = os.getenv("TG_API_HASH", "")
session_name = "me_session"

# ====== 加载配置文件 ======
with open("config.yml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

tasks = config.get("tasks", [])

client = TelegramClient(session_name, api_id, api_hash)

def log(message: str):
    """打印带北京时间戳的日志"""
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}")

async def schedule_task(chat, time_str, text):
    while True:
        now = datetime.now(tz)
        target_time = datetime.strptime(time_str, "%H:%M").time()
        next_run = datetime.combine(now.date(), target_time)
        next_run = tz.localize(next_run)

        if now.time() > target_time:
            next_run += timedelta(days=1)

        wait = (next_run - now).total_seconds()
        log(f"[{chat}] 下次发送时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}, 内容: {text}")
        await asyncio.sleep(wait)

        try:
            await client.send_message(chat, text)
            log(f"✅ [{chat}] 已发送: {text}")
        except Exception as e:
            log(f"❌ [{chat}] 发送失败: {e}")
            traceback.print_exc()

async def main():
    await client.start()
    coroutines = [schedule_task(t["chat"], t["time"], t["text"]) for t in tasks]
    await asyncio.gather(*coroutines)

if __name__ == "__main__":
    client.loop.run_until_complete(main())
