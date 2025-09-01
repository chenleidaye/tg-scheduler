import os
import asyncio
from datetime import datetime, timedelta
import pytz
import yaml
from telethon import TelegramClient, events

# ---------------- 配置文件 ----------------
CONFIG_FILE = "/app/config.yml"
LOG_FILE = "/app/tg-scheduler.log"

# ---------------- 日志函数 ----------------
def log(message: str):
    now = datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {message}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"[日志错误] {e}", flush=True)

# ---------------- 读取配置 ----------------
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

api_id = config["telegram"]["api_id"]
api_hash = config["telegram"]["api_hash"]
notify_bot_token = config["telegram"]["notify_bot_token"]
notify_user = config["telegram"]["notify_user"]
checkin_bot_id = config["telegram"]["checkin_bot_id"]
keywords = config["telegram"]["keywords"]

jobs = config.get("jobs", [])

# ---------------- 客户端初始化 ----------------
client = TelegramClient("/app/me_session.session", api_id, api_hash)
notify_bot = TelegramClient("notify_bot", api_id, api_hash).start(bot_token=notify_bot_token)

# 保存你发送的签到消息 id
sent_message_ids = set()

# ---------------- 定时任务 ----------------
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
        msg = await client.send_message(chat_id, content)
        sent_message_ids.add(msg.id)
        log(f"[{chat_id}] ✅ 已发送消息: {content}, id={msg.id}")

# ---------------- 监听 Bot 回复 ----------------
@client.on(events.NewMessage)
async def handler(event):
    if event.sender_id != checkin_bot_id:
        return
    if event.reply_to_msg_id not in sent_message_ids:
        return
    msg_text = event.raw_text
    if any(k in msg_text for k in keywords):
        try:
            await notify_bot.send_message(notify_user, f"已转发签到反馈: {msg_text}")
            log(f"已转发签到反馈: {msg_text}")
        except Exception as e:
            log(f"❌ 转发失败: {e}")

# ---------------- 日志清理 ----------------
async def clear_logs_periodically():
    while True:
        await asyncio.sleep(7 * 24 * 60 * 60)  # 每7天
        try:
            if os.path.exists(LOG_FILE):
                open(LOG_FILE, "w").close()
                log("🧹 日志已清理")
        except Exception as e:
            log(f"❌ 日志清理失败: {e}")

# ---------------- 主函数 ----------------
async def main():
    asyncio.create_task(clear_logs_periodically())

    # 启动所有定时任务
    tasks = [schedule_task(job["chat_id"], job["time"], job["message"]) for job in jobs]

    await client.start()
    log("tg-scheduler 已启动")
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
