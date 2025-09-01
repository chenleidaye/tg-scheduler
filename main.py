import asyncio
import yaml
from datetime import datetime, timedelta
import pytz
from telethon import TelegramClient, events

# 读取配置
with open("config.yml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

tg_conf = config["telegram"]
api_id = tg_conf["api_id"]
api_hash = tg_conf["api_hash"]
notify_bot_token = tg_conf["notify_bot_token"]
notify_user = tg_conf["notify_user"]
checkin_bot_id = tg_conf["checkin_bot_id"]
keywords = tg_conf["keywords"]

jobs = config.get("jobs", [])

# 你的主账号 session
client = TelegramClient("me_session.session", api_id, api_hash)
# 用于发送通知的 Bot
notify_bot = TelegramClient("notify_bot.session", api_id, api_hash).start(bot_token=notify_bot_token)

tz = pytz.timezone("Asia/Shanghai")

async def send_scheduled_message(chat_id, send_time, text):
    while True:
        now = datetime.now(tz)
        target = tz.localize(datetime.combine(now.date(), datetime.strptime(send_time, "%H:%M").time()))
        if now >= target:
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        print(f"[{chat_id}] 下次发送时间: {target}, 内容: {text}")
        await asyncio.sleep(wait_seconds)
        await client.send_message(chat_id, text)
        print(f"[{chat_id}] ✅ 已发送: {text}")

# 监听签到 Bot 的消息
@client.on(events.NewMessage(from_users=checkin_bot_id))
async def handler(event):
    msg_text = event.raw_text
    if any(k in msg_text for k in keywords):
        await notify_bot.send_message(notify_user, f"已转发签到反馈: {msg_text}")
        print(f"✅ 已通过 notify bot 转发消息: {msg_text}")

async def main():
    # 启动定时任务
    tasks = []
    for job in jobs:
        tasks.append(send_scheduled_message(job["chat_id"], job["time"], job["message"]))
    # 并行运行
    await asyncio.gather(client.start(), *tasks)

if __name__ == "__main__":
    asyncio.run(main())
