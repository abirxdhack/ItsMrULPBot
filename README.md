# 🤖 ItsMrULPBot

A powerful async Telegram bot built with Telethon for searching, extracting, and processing ULP (URL:Login:Password) databases — with admin tools, combo generation, and smart file management.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![Telethon](https://img.shields.io/badge/Telethon-Latest-green)](https://github.com/LonamiWebs/Telethon)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## ✨ Features

- 🔍 Keyword-based ULP search across large databases
- 📤 Extract mail:pass, user:pass, number:pass combos
- 🗂️ Combo generation with format selection
- 📁 Database file viewer with pagination
- 🧹 DB and dump cleanup tools for admins
- 📡 File upload with real-time progress bar
- ⚡ Async + uvloop for high-performance processing
- 🛡️ Owner & admin-only restricted commands
- 🔁 Auto cleanup of processed/temporary files

---

## 🧰 Requirements

- Python 3.11+
- [`ripgrep`](https://github.com/BurntSushi/ripgrep) installed as a system binary (`rg`)
- Telegram API credentials (API ID, API Hash, Bot Token)
- See `requirements.txt` for Python dependencies

### Install ripgrep

**Debian / Ubuntu:**
```bash
apt install ripgrep
```

**Arch Linux:**
```bash
pacman -S ripgrep
```

**macOS:**
```bash
brew install ripgrep
```

---

## 📦 Installation

```bash
git clone https://github.com/abirxdhack/ItsMrULPBot
cd ItsMrULPBot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## ⚙️ Configuration

Open `config.py` and fill in your values:

```python
API_ID       = 0              # Your Telegram API ID
API_HASH     = ''             # Your Telegram API Hash
BOT_TOKEN    = ''             # Your Bot Token from @BotFather
OWNER_ID     = 0              # Your Telegram user ID
ADMIN_ID     = 0              # Admin Telegram user ID
UPDATE_CHANNEL_URL = 't.me/yourchannel'
COMMAND_PREFIXES   = ['/', '!', '.']
```

Get your API credentials at [my.telegram.org](https://my.telegram.org).

---

## 🗄️ Database Setup

Place your `.txt` ULP database files inside the `data/` folder:

```
ItsMrULPBot/
├── data/
│   ├── database1.txt
│   ├── database2.txt
│   └── ...
```

Each file should contain one record per line in any of these formats:

```
url:email:password
url:username:password
url:phonenumber:password
```

---

## ▶️ Run Bot

```bash
python main.py
```

---

## 💬 Commands

### Public Commands

| Command | Description |
|---|---|
| `/start` | Show welcome message |
| `/help` | Show help message |
| `/cmds` | List all commands |
| `/ulp <keyword>` | Search ULP database by keyword |
| `/extract <keyword>` | Extract specific format from keyword or file |
| `/cmb <keyword>` | Generate combo file for a keyword |

### Admin / Owner Commands

| Command | Description |
|---|---|
| `/add` | Upload and add `.txt` database files to the server |
| `/files` | Browse all database files with Next/Previous navigation |
| `/clean` | View DB stats and access cleanup tools |

---

## 🗂️ Project Structure

```
ItsMrULPBot/
├── main.py              # Entry point — loads all handlers and starts bot
├── bot.py               # TelegramClient instance
├── config.py            # Bot configuration
├── core/
│   └── start.py         # /start command handler
├── modules/
│   ├── help.py          # /help and /cmds handler
│   ├── ulp.py           # /ulp search handler
│   ├── extract.py       # /extract handler
│   ├── cmb.py           # /cmb combo handler
│   ├── add.py           # /add database upload handler
│   ├── clean.py         # /clean and /files admin handler
│   └── callback.py      # Inline button callback handler
├── helpers/
│   ├── botutils.py      # send_message, edit_message, etc.
│   ├── buttons.py       # SmartButtons inline keyboard builder
│   ├── func.py          # Search and file write logic
│   ├── pgbar.py         # Upload progress bar
│   ├── utils.py         # new_task, clean_download helpers
│   └── logger.py        # Logging setup
├── utils/
│   └── engine.py        # Core ripgrep search engine wrapper
├── data/                # Place your .txt ULP databases here
├── downloads/           # Temporary output files (auto-cleaned)
├── requirements.txt
└── pyproject.toml
```

---

## ⚠️ Notes

- The `downloads/` folder is auto-cleaned after every file is sent.
- Only **Owner** and **Admin** can use `/add`, `/files`, and `/clean`.
- All other users are silently ignored on restricted commands.
- Intended for private/personal use only — handle databases responsibly.

---

## 👤 Credits

- 👨‍💻 Dev: **@ISmartCoder**
- 📢 Updates: **@abirxdhackz**
