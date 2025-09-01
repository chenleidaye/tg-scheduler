import os
import asyncio
from datetime import datetime, timedelta
import pytz
import yaml
from telethon import TelegramClient, events

# 日志文件路径
LOG_FILE = "/app/tg-scheduler.log"

def log(message: str):
    """打印日志 + 写入文件"""
    现在 = datetime.当前(pytz.timezone("Asia/Shanghai"))。strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{当前}] {message}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"[日志错误] {e}", flush=True)

async def send_message(client, chat_id: int, text: str):
    """发送消息到指定 chat"""
    try:
        await client.send_message(chat_id, text)
        log(f"[{chat_id}] ✅ 发送消息: {text}")
    except Exception as e:
        log(f"[{chat_id}] ❌ 发送失败: {e}")

async def schedule_task(client, chat_id: int, send_time: str, content: str):
    """定时任务：每天在指定时间发送消息"""
    tz = pytz.timezone("Asia/Shanghai")
    while True:
        now = datetime.now(tz)
        target = tz.localize(datetime.combine(现在.date(), datetime.strptime(send_time, "%H:%M").time()))
        if now >= target:
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        log(f"[{chat_id}] 下次发送时间: {target}, 内容: {content}")
        await asyncio.sleep(wait_seconds)
        await send_message(client, chat_id, content)

async def clear_logs_periodically():
    """每 7 天清理日志"""
    while True:
        await asyncio.sleep(7*24*60*60)
        try:
            if os.path.exists(LOG_FILE):
                open(LOG_FILE, "w").close()
                log("🧹 日志已清理")
        except Exception as e:
            log(f"❌ 日志清理失败: {e}")

async def main():
    # 读取配置
    with open("/app/config.yml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    api_id = config["telegram"]["api_id"]
    api_hash = config["telegram"]["api_hash"]
    session_name = config["telegram"]["session"]
    notify_user = config["telegram"]["notify_user"]        # 你的 TG ID
    checkin_bot_id = config["telegram"]["checkin_bot_id"]  # 签到 Bot 的 ID
    keywords = config["telegram"]["keywords"]              # 签到相关关键字

    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()

    log("tg-scheduler 已启动")

    # === 监听签到反馈（只转发你自己的消息） ===
    @client.on(events.NewMessage(from_users=checkin_bot_id))
    async def handler(event):
        if event.is_reply:
            reply_msg = await event.get_reply_message()
            if reply_msg.sender_id == notify_user:
                if any(kw in reply_msg.message for kw in keywords) or \
                   any(kw in event.raw_text for kw in keywords):
                    await client.send_message(notify_user, f"📌 签到反馈:\n{event.raw_text}")
                    log(f"已转发签到反馈: {event.raw_text}")

    # === 并发运行定时任务和日志清理 ===
    tasks = [clear_logs_periodically()]
    for job in config["jobs"]:
        tasks.append(schedule_task(client, job["chat_id"], job["time"], job["message"]))

    await asyncio.gather(*tasks, client.run_until_disconnected())

if __name__ == "__main__":
    asyncio.run(main())
