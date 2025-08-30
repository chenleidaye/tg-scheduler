好的 👍 我帮你写一个完整的 README.md，方便你在 GitHub 仓库展示和查看。

📄 README.md

# 📌 TG-Scheduler

[![Docker](https://img.shields.io/badge/Docker%20Hub-gvddfdf%2Ftg--scheduler-blue)](https://hub.docker.com/r/gvddfdf/tg-scheduler)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/chenleidaye/tg-scheduler/docker.yml?branch=main)](https://github.com/chenleidaye/tg-scheduler/actions)

一个基于 [Telethon](https://github.com/LonamiWebs/Telethon) 的 **Telegram 定时消息工具**，支持账号身份（非 Bot），可在指定时间自动向群组/频道发送消息。  
适用于 **签到、打卡、定时提醒** 等场景。

---

## ✨ 功能特性
- 使用 Telegram **账号** 发送消息（非 Bot）
- 任务配置独立在 `config.yml`，无需修改代码
- 支持多群、多条消息定时任务
- Docker 容器化，部署简单
- GitHub Actions 自动构建并推送到 Docker Hub

---

## 📦 使用方法

### 1. 克隆项目
```bash
git clone https://github.com/chenleidaye/tg-scheduler.git
cd tg-scheduler

2. 编辑配置文件

修改 config.yml，示例：

tasks:
  - chat: -1001234567890     # 群组/频道 ID 或 @用户名
    time: "00:00"            # 每天的时间（24小时制）
    text: "赌狗签到"         # 要发送的内容

  - chat: "@mygroup"
    time: "09:00"
    text: "早安打卡"

3. 本地运行

安装依赖：

pip install -r requirements.txt

运行：

python main.py

首次运行会提示输入手机号和验证码，生成 me_session.session 文件，后续无需再次登录。

🐳 Docker 部署

拉取镜像

docker pull gvddfdf/tg-scheduler:latest

启动容器

docker run -d \
  --name tg-scheduler \
  -e TG_API_ID=123456 \
  -e TG_API_HASH=abcdef1234567890abcdef1234567890 \
  -v $(pwd)/config.yml:/app/config.yml \
  -v $(pwd)/me_session.session:/app/me_session.session \
  gvddfdf/tg-scheduler:latest

🔧 环境变量

变量名	说明	示例
TG_API_ID	Telegram API ID（必填）	123456
TG_API_HASH	Telegram API Hash（必填）	abcdef1234567890abcdef1234567890
