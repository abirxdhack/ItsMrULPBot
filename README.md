# 🚀 ItsMrULPBot

**The Ultimate Logs ➡️ ULP ➡️ Combo Maker!**  
A lightning-fast, fully asynchronous Telegram bot built with [Pyrofork](https://github.com/pyrogram/pyrofork) & `asyncio`.  
Transform logs, ULPs (User:Login:Password), and combos in seconds!  
Made with ❤️ by [@abirxdhack](https://github.com/abirxdhack)

---

<p align="center">
  <img src="https://img.shields.io/github/stars/abirxdhack/ItsMrULPBot?style=social" alt="GitHub stars">
  <img src="https://img.shields.io/github/forks/abirxdhack/ItsMrULPBot?style=social" alt="GitHub forks">
  <img src="https://img.shields.io/badge/Made%20with-Pyrofork-blue?logo=python" alt="Pyrofork">
  <img src="https://img.shields.io/badge/Asyncio-%E2%9C%85-green" alt="Async">
</p>

---

## ✨ What Makes ItsMrULPBot Awesome?

- **Ultra Fast:** Built entirely on asyncio for maximum speed and scale.
- **Multi-Format Magic:** Instantly convert logs ↔️ ULP ↔️ combos of any type.
- **Admin & User Modes:** Full set of admin and user tools for total control.
- **Cloud-Ready:** Designed for high-load, supreme hosting (Azure, AWS, RDP, etc.)
- **MongoDB Power:** Robust, scalable backend for storing and managing everything.

---

## 🛡️ Command Cheat Sheet

### 👑 Admin / Sudo Commands
| Command | Description |
| ------- | ----------- |
| `add`   | Add a user to premium |
| `db`    | View Logs/ULP directory |
| `del`   | Delete Logs/ULP directory |
| `feed`  | Feed logs to DB |
| `stop`  | Stop feed & upload files |
| `all`   | List all users (from MongoDB) |

### 🧑‍💻 User Commands
| Command  | Description |
| -------- | ----------- |
| `ulp`    | Get ULP for any site/URL |
| `num`    | Get num:pass combo from a file |
| `user`   | Get user:pass combo from a file |
| `email`  | Get mail:pass combo |
| `ping`   | Bot status & speedtest |
| `info`   | View your info & subscription |

---

## 🗂️ Project Structure

```
ItsMrULPBot/
│
├── core/
│   ├── mongo.py
│   ├── start.py
│   └── __init__.py
│
├── utils/
│   ├── logging_setup.py
│   └── __init__.py
│
├── plugins/
│   ├── all.py
│   ├── filter.py
│   ├── find.py
│   ├── info.py
│   ├── tools.py
│   ├── ulp.py
│   └── up.py
│
├── app.py
├── main.py
├── config.py
├── requirements.txt
```

---

## ⚡ Quickstart: Deploy Your Own

### 🐧 On Ubuntu
```bash
pip3 install -r requirements.txt
screen -S ItsMrULPBot
python3 main.py
```

### 🪟 On Windows/RDP
```bash
pip install -r requirements.txt
python main.py
```

### 🍴 Clone & Go!
```bash
git clone https://github.com/abirxdhack/ItsMrULPBot
cd ItsMrULPBot
```

---

## 🏎️ Recommended Hosting

**This is a high-performance bot! For best results, use a Supreme server:**  
**Azure RDP, Amazon AWS, or a top-tier VPS.**  
Don't host on potato servers. 🥔❌

---

## ⚙️ Configuration: Plug in Your Secrets

Open `config.py` and fill in all required details:

```python
# Bot configuration
API_ID = YOUR_API_ID
API_HASH = "YOUR_API_HASH"
BOT_TOKEN = "YOUR_BOT_TOKEN"

# Command prefixes
COMMAND_PREFIX = [",", ".", "/", "!"]

# Developer details
DEVELOPER_ID = YOUR_USER_ID  # Your Telegram user ID (numeric)
UPDATES_CHANNEL = "YOUR_CHANNEL_URL"  # (Optional) Updates channel URL

ADMIN_IDS = [FIRST_ADMIN_ID, SECOND_ADMIN_ID]  # Telegram user IDs for admins

# MongoDB configuration
MONGO_URL = "YOUR_MONGO_URL"
```

### 🔑 Where do I get these?

- **API_ID & API_HASH:** [my.telegram.org](https://my.telegram.org) → Log in → API development tools  
- **BOT_TOKEN:** Talk to [@BotFather](https://t.me/BotFather) on Telegram  
- **DEVELOPER_ID & ADMIN_IDS:** Get your Telegram numeric ID via [@userinfobot](https://t.me/userinfobot)  
- **UPDATES_CHANNEL:** (Optional) Your Telegram channel URL  
- **MONGO_URL:** From [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) or your own MongoDB server

---

## 🤝 Credits

- Powered by [Pyrofork](https://github.com/pyrogram/pyrofork)
- Async magic via [asyncio](https://docs.python.org/3/library/asyncio.html)
- Built with ❤️ by [@abirxdhack](https://github.com/abirxdhack)

---

## ⭐️ Show Some Love!

If this bot made your life easier,  
**star the repo** and share the love!

[![Star on GitHub](https://img.shields.io/github/stars/abirxdhack/ItsMrULPBot?style=social)](https://github.com/abirxdhack/ItsMrULPBot)

---
