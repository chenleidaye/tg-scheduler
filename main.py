import os
import asyncio
import json
import logging
import signal
import functools
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, time, timedelta
from typing import Set
import pytz
import yaml
from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import RpcError

# --- 配置与设置 (Configuration & Setup) ---

# 使用 __file__ 获取当前脚本所在目录，确保路径在任何环境下都正确
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.yml")
LOG_FILE = os.path.join(BASE_DIR, "tg-scheduler.log")
SESSION_DIR = BASE_DIR
STATE_FILE = os.path.join(BASE_DIR, "sent_message_ids.json")

# --- 标准化日志 (Standardized Logging) ---
# 设置一个日志记录器，该记录器会每周一轮换日志文件，并保留4周的备份
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# 日志格式更详细，包含模块名和行号，便于调试
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)')

# 为了保持日志时间戳的一致性，统一使用 UTC 时间
# formatter.converter = lambda *args: datetime.now(pytz.utc).timetuple() # 可选：如果需要UTC时间戳

# 控制台处理器 (Console Handler)
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

# 带时间轮换的文件处理器 (File Handler with Timed Rotation)
try:
    # 'W0' 表示每周一 (Monday) 进行轮换
    fh = TimedRotatingFileHandler(LOG_FILE, when="W0", backupCount=4, encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
except Exception as e:
    logger.error(f"设置文件日志失败 (Failed to set up file logging): {e}")

# --- 加载配置 (Load Configuration) ---
try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    logger.critical(f"配置文件未找到 (Configuration file not found at) {CONFIG_FILE}. 程序退出。")
    exit(1)
except Exception as e:
    logger.critical(f"读取配置文件时出错 (Error reading configuration file): {e}. 程序退出。")
    exit(1)

# 从配置中读取参数
api_id = config["telegram"]["api_id"]
api_hash = config["telegram"]["api_hash"]
notify_bot_token = config["telegram"]["notify_bot_token"]
notify_user = config["telegram"]["notify_user"]
checkin_bot_id = config["telegram"]["checkin_bot_id"]
jobs = config.get("jobs", [])

# --- 状态管理 (State Management) ---
# 从文件中加载已发送的消息ID，以便在程序重启后状态不丢失
def load_sent_ids() -> Set[int]:
    """从 JSON 文件加载已发送消息 ID 集合。"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"无法加载状态文件 (Could not load state file): {e}. 将创建新的状态。")
    return set()

def save_sent_ids(ids_set: Set[int]):
    """将已发送消息 ID 集合保存到 JSON 文件。"""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(list(ids_set), f, indent=2)
    except IOError as e:
        logger.error(f"无法将状态保存至 (Failed to save state to) {STATE_FILE}: {e}")

sent_message_ids = load_sent_ids()


# --- 核心逻辑 (Main Logic) ---

async def send_checkin(client: TelegramClient, job_name: str, chat_id: int, message: str):
    """发送消息，并对潜在的 Telegram API 错误进行健壮处理。"""
    try:
        msg = await client.send_message(chat_id, message)
        sent_message_ids.add(msg.id)
        save_sent_ids(sent_message_ids)  # 立即持久化状态
        logger.info(f"[{job_name}] ✅ 成功发送消息 (id={msg.id}): {message}")
    except RpcError as e:
        logger.error(f"[{job_name}] ❌ 因 Telegram API 错误导致发送失败: {e}")
    except Exception as e:
        logger.error(f"[{job_name}] ❌ 发送消息时发生未知错误: {e}")

async def schedule_task(client: TelegramClient, job_name: str, chat_id: int, send_time_str: str, content: str):
    """调度一个带时区感知的每日重复任务。"""
    tz = pytz.timezone("Asia/Shanghai")
    try:
        send_time = datetime.strptime(send_time_str, "%H:%M").time()
    except ValueError:
        logger.error(f"[{job_name}] 无效的时间格式 '{send_time_str}'。应为 HH:MM 格式。该任务不会运行。")
        return

    logger.info(f"[{job_name}] 任务已调度，将于每日 {send_time_str} (Asia/Shanghai) 执行，消息: '{content}'")

    while True:
        try:
            now = datetime.now(tz)
            target_datetime = tz.localize(datetime.combine(now.date(), send_time))

            if now >= target_datetime:
                target_datetime += timedelta(days=1)

            wait_seconds = (target_datetime - now).total_seconds()
            logger.info(f"[{job_name}] 下次运行于 {target_datetime.strftime('%Y-%m-%d %H:%M:%S')}. 等待 {wait_seconds:.0f} 秒。")

            await asyncio.sleep(wait_seconds)

            # 在发送前再次检查时间，以避免因系统休眠等原因造成的漂移
            if datetime.now(tz) >= target_datetime:
                await send_checkin(client, job_name, chat_id, content)
        except asyncio.CancelledError:
            logger.info(f"任务 [{job_name}] 已被取消。")
            break # 退出循环
        except Exception as e:
            logger.error(f"任务 [{job_name}] 循环中发生错误: {e}")
            await asyncio.sleep(60) # 发生错误后等待一分钟再重试


async def shutdown(sig: signal.Signals, loop: asyncio.AbstractEventLoop, tasks: list):
    """优雅地关闭应用程序，取消所有正在运行的任务。"""
    logger.warning(f"接收到退出信号 {sig.name}...")
    logger.warning("正在取消所有后台任务...")

    # 向所有任务发送取消请求
    for task in tasks:
        task.cancel()

    # 等待所有任务完成取消操作
    await asyncio.gather(*tasks, return_exceptions=True)

    logger.info("所有任务已取消。正在关闭客户端...")
    # 停止事件循环，这将导致 run_until_disconnected 返回
    loop.stop()


async def main():
    """初始化客户端，设置事件处理器，并运行所有调度任务。"""
    background_tasks = []
    loop = asyncio.get_running_loop()

    # 使用相对路径存储 session 文件
    user_client = TelegramClient(os.path.join(SESSION_DIR, "me_session"), api_id, api_hash)
    notify_bot = TelegramClient(os.path.join(SESSION_DIR, "notify_bot"), api_id, api_hash)

    # 在 main 作用域内定义事件处理器，以便访问 notify_bot
    @user_client.on(events.NewMessage(from_users=checkin_bot_id))
    async def handler(event):
        reply_msg_id = event.message.reply_to_msg_id
        if reply_msg_id in sent_message_ids:
            msg_text = event.message.message
            logger.info(f"收到消息 {reply_msg_id} 的回复。正在转发给用户...")
            try:
                await notify_bot.send_message(notify_user, f"✅ **签到回复已收到:**\n\n`{msg_text}`", parse_mode='md')
            except RpcError as e:
                logger.error(f"通过通知机器人转发回复失败: {e}")
            finally:
                # 处理完后清理旧的消息ID，防止状态文件无限增长
                sent_message_ids.remove(reply_msg_id)
                save_sent_ids(sent_message_ids)

    logger.info("正在启动 Telegram 调度器...")

    # 设置信号处理器以实现优雅关闭
    for sig in (signal.SIGINT, signal.SIGTERM):
        # 使用 functools.partial 将参数传递给处理器
        shutdown_handler = functools.partial(shutdown, sig, loop, background_tasks)
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown_handler()))

    try:
        await notify_bot.start(bot_token=notify_bot_token)
        logger.info("通知机器人客户端启动成功。")
        # 发送启动通知
        await notify_bot.send_message(notify_user, f"🚀 **调度器已启动**\n\n版本: {datetime.now().strftime('%Y%m%d-%H%M')}\n已加载 {len(jobs)} 个任务。")
    except Exception as e:
        logger.critical(f"启动通知机器人客户端失败: {e}")
        return

    # 使用 async with 确保 user_client 在结束时能被正确关闭
    async with user_client:
        logger.info("用户客户端启动成功。")

        # 并发创建并运行所有调度任务
        for job in jobs:
            # 为每个任务提供一个唯一的名称，如果配置中没有则自动生成
            job_name = job.get("name", f"Chat-{job['chat_id']}-{job['time']}")
            task = asyncio.create_task(
                schedule_task(user_client, job_name, job["chat_id"], job["time"], job["message"])
            )
            background_tasks.append(task)
        
        logger.info(f"已启动 {len(background_tasks)} 个调度任务。")
        
        # 此调用将永久运行，保持客户端存活以接收事件，直到被信号中断
        await user_client.run_until_disconnected()

    # 清理
    await notify_bot.disconnect()
    logger.info("所有客户端已断开连接。程序关闭。")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("调度器被用户手动停止。")

