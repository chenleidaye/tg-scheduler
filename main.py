import os
import asyncio
from datetime import datetime, timedelta
import pytz
import yaml
from telethon import TelegramClient, events

# ================= 配置 =================
CONFIG_PATH = "/app/config.yml"
LOG_FILE = "/app/tg-scheduler.log"

# 读取配置
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

tg_cfg = config["telegram"]
jobs = config.get("jobs", [])

API_ID = tg_cfg["api_id"]
API_HASH = tg_cfg["api_hash"]
SESSION_FILE = "/app/me_session.session"
NOTIFY_USER = tg_cfg["notify_user"]
CHECKIN_BOT_ID = tg_cfg["checkin_bot_id"]
KEYWORDS = tg_cfg.get("keywords", ["签到", "打卡", "成功", "奖励"])

# ================= 日志 =================
def log(msg: str):
    now = datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"[日志错误] {e}", flush=True)

# ================= 定时任务 =================
async def schedule_task(client: TelegramClient, chat_id: int, send_time: str, message: str):
    tz = pytz.timezone("Asia/Shanghai")
    while True:
        now = datetime.now(tz)
        target = tz.localize(datetime.combine(now.date(), datetime.strptime(send_time, "%H:%M").time()))
        if now >= target:
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        log(f"[{chat_id}] 下次发送时间: {target}, 内容: {message}")
        await asyncio.sleep(wait_seconds)
        await client.send_message(chat_id, message)
        log(f"[{chat_id}] ✅ 已发送消息: {message}")

# ================= 日志清理 =================
async def clear_logs_periodically():
    while True:
        await asyncio.sleep(7 * 24 * 60 * 60)  # 7天
        try:
            if os.path.exists(LOG_FILE):
                open(LOG_FILE, "w").close()
                log("🧹 日志已清理")
        except Exception as e:
            log(f"❌ 日志清理失败: {e}")

# ================= 签到反馈监听 =================
async def setup_event_handler(client: TelegramClient):
    @client.on(events.NewMessage())
    async def handler(event):
        msg = event.message
        sender = msg.sender_id
        text = msg.message or ""
        if sender == CHECKIN_BOT_ID and any(k in text for k in KEYWORDS):
            await client.send_message(NOTIFY_USER, f"已转发签到反馈: {text}")
            log(f"已转发签到反馈: {text}")

# ================= 主程序 =================
async def main():
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.start()
    log("tg-scheduler 已启动")

    # 启动日志清理
    asyncio.create_task(clear_logs_periodically())

    # 监听签到反馈
    await setup_event_handler(client)

    # 启动定时任务
    tasks = []
    for job in jobs:
        tasks.append(schedule_task(client, job["chat_id"], job["time"], job["message"]))
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
