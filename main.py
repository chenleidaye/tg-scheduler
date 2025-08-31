import os
import asyncio
from datetime import datetime, timedelta
import pytz

# 日志文件路径
LOG_FILE = "/app/tg-scheduler.log"

def log(message: str):
    """打印日志到控制台 + 写入日志文件"""
    now = datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {message}"
    print(line, flush=True)  # 控制台日志（docker logs 可见）
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"[日志错误] {e}", flush=True)


async def send_message(chat_id: int, text: str):
    """
    模拟发送消息（这里你可以换成真实的 Telegram API 调用）
    """
    log(f"[{chat_id}] ✅ 发送消息: {text}")


async def schedule_task(chat_id: int, send_time: str, content: str):
    """
    定时任务：每天在指定时间发送消息
    send_time: "HH:MM" (北京时间)
    """
    tz = pytz.timezone("Asia/Shanghai")

    while True:
        now = datetime.now(tz)
        target = tz.localize(datetime.combine(now.date(), datetime.strptime(send_time, "%H:%M").time()))

        # 如果今天的时间已经过了，推到明天
        if now >= target:
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        log(f"[{chat_id}] 下次发送时间: {target}, 内容: {content}")

        await asyncio.sleep(wait_seconds)
        await send_message(chat_id, content)


async def clear_logs_periodically():
    """
    每 7 天清理一次日志文件
    """
    while True:
        await asyncio.sleep(7 * 24 * 60 * 60)  # 7 天
        try:
            if os.path.exists(LOG_FILE):
                open(LOG_FILE, "w").close()  # 清空日志
                log("🧹 日志已清理")
        except Exception as e:
            log(f"❌ 日志清理失败: {e}")


async def main():
    # 启动清理日志任务
    asyncio.create_task(clear_logs_periodically())

    # 示例任务（每天 02:00 发送“赌狗签到”）
    await asyncio.gather(
        schedule_task(-1001379449445, "02:00", "赌狗签到"),
        # 你可以继续添加其他任务 ↓
        # schedule_task(-1001379449445, "08:00", "早安消息"),
    )


if __name__ == "__main__":
    asyncio.run(main())
