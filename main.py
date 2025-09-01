import os
import asyncio
from datetime import datetime, timedelta
import pytz
import yaml
from telethon import TelegramClient, events

# 日志文件路径
LOG_FILE = "/app/tg-scheduler.log"

def log(message: str):
    now = datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {message}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"[日志错误] {e}", flush=True)

# 读取配置
with open("/app/config.yml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

api_id = config["telegram"]["api_id"]
api_hash = config["telegram"]["api_hash"]
notify_bot_token = config["telegram"]["notify_bot_token"]
notify_user = config["telegram"]["notify_user"]
checkin_bot_id = config["telegram"]["checkin_bot_id"]

jobs = config.get("jobs", [])

# 客户端
client = TelegramClient("/app/me_session.session", api_id, api_hash)
notify_bot = TelegramClient("/app/notify_bot.session", api_id, api_hash)

# 保存你发送的签到消息ID
sent_message_ids = set()

async def send_checkin(chat_id, message):
    msg = await client.send_message(chat_id, message)
    sent_message_ids.add(msg.id)
    log(f"[{chat_id}] ✅ 已发送签到消息: {message} (id={msg.id})")

@client.on(events.NewMessage(from_users=checkin_bot_id))
async def handler(event):
    reply_msg_id = event.message.reply_to_msg_id
    if reply_msg_id in sent_message_ids:
        msg_text = event.message.message
        await notify_bot.send_message(notify_user, f"已转发签到反馈: {msg_text}")
        log(f"已转发签到反馈: {msg_text}")

async def schedule_task(chat_id: int, send_time: str, content: str):
    tz = pytz.timezone("Asia/Shanghai")
    while True:
        now = datetime.now(tz)
        target = tz.localize(datetime.combine(now.date(), datetime.strptime(send_time, "%H:%M").time()))
        if now >= target:
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        log(f"[{chat_id}] 下次发送时间: {target}, 内容: {content}")
        await asyncio.sleep(wait_seconds)
        await send_checkin(chat_id, content)

async def clear_logs_periodically():
    while True:
        await asyncio.sleep(7 * 24 * 60 * 60)  # 7天
        try:
            if os.path.exists(LOG_FILE):
                open(LOG_FILE, "w").close()
                log("🧹 日志已清理")
        except Exception as e:
            log(f"❌ 日志清理失败: {e}")

async def main():
    await client.start()
    await notify_bot.start(bot_token=notify_bot_token)
    log("tg-scheduler 已启动")

    # 启动日志清理任务
    asyncio.create_task(clear_logs_periodically())

    # 启动定时任务
    tasks = []
    for job in jobs:
        tasks.append(schedule_task(job["chat_id"], job["time"], job["message"]))
    await asyncio.gather(*tasks, client.run_until_disconnected(), notify_bot.run_until_disconnected())

if __name__ == "__main__":
    asyncio.run(main())
