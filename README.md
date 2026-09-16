# Portable AI Agent — ایجنت هوشمند و آفلاین اتوماسیون وب و بله

پلتفرم پیشرفته، آفلاین و قابل‌حمل **ایجنت هوشمند و اتوماسیون مرورگر** از طریق پروتکل CDP (Chrome DevTools Protocol)، با قابلیت توسعه ماژولار اسکیل‌ها، اتصال MCP، تونل‌زنی امن در شبکه ایزوله و ارتباط با مدل‌های هوش مصنوعی.

[English Summary](#english-summary) | [راهنمای فارسی](#راهنمای-فارسی)

---

## 🌟 معماری جدید ایجنت هوشمند (Modular AI Agent Architecture)

این پروژه از یک ابزار ساده به یک **پلتفرم جامع ایجنت هوشمند** ارتقا یافته است:

```
+-------------------------------------------------------+       +-------------------------------------------------------+
|  محیط ایزوله سازمانی (Isolated Enterprise Network)   |       |             محیط اینترنتی (Internet Gateway)         |
|  - دسترسی غیر ادمین ویندوز                            |       |  - دسترسی به اینترنت و API مدل‌های هوش مصنوعی         |
|  - بدون نیاز به اینترنت                               |       |                                                       |
|                                                       |       |                                                       |
|  +-------------------------------------------------+  |       |  +-------------------------------------------------+  |
|  |           Agent Core Engine (هسته اصلی)         |  |       |  |          Bale AI Gateway (گیت‌وی هوشمند)        |  |
|  |  - CDP Automation Engine (26+ Actions)          |  |       |  |  - Claude / OpenAI / Ollama LLM Adapters       |  |
|  |  - Dynamic Skill Engine + HMAC Verification     |  |       |  |  - Scenario Generator & Code Synthesizer        |  |
|  |  - Local RAG Memory (SQLite FTS5 + BM25)        |  |       |  |  - Vector RAG Knowledge Base                   |  |
|  |  - MCP Server (Model Context Protocol)          |  |       |  |  - MCP Tool Registry                           |  |
|  +-----------------------+-------------------------+  |       |  +-----------------------+-------------------------+  |
|                          |                            |       |                          |                            |
|                          v                            |       |                          v                            |
|  +-------------------------------------------------+  |       |  +-------------------------------------------------+  |
|  |       Bale Worker Bot (ربات محلی HTTP/CDP)       |  |       |  |          Bale Gateway Bot (ربات گیت‌وی)          |  |
|  |  - SHA256-CTR + HMAC-SHA256 Encrypted Tunnel    |  |       |  |  - Protocol Deserializer & Command Handler         |  |
|  +-----------------------+-------------------------+  |       |  +-----------------------+-------------------------+  |
+--------------------------|----------------------------+       +--------------------------|----------------------------+
                           |                                                               |
                           +=================== کانال متنی بله ============================+
                                 (Bale Messenger Protocol / Text Tunnel)
```

---

## ✨ ویژگی‌های جدید و کلیدی

1. **🧠 هسته ماژولار ایجنت (`agent_core.py`):** مدیریت چرخه‌حیات ایجنت، اجرای اسکیل‌ها و مدیریت حالت به صورت سرویس/کنسول.
2. **🔌 سیستم اسکیل‌های امن با امضا (`skill_manager.py`):** تعریف، امضا (HMAC-SHA256) و اعتبارسنجی اسکیل‌های JSON یا پایتون قبل از اجرا.
3. **🤖 پروتکل MCP اختصاصی (`mcp_adapter.py`):** پیاده‌سازی استاندارد Model Context Protocol جهت اتصال ابزارهای ایجنت به Claude Desktop و Cursor.
4. **🔐 تونل متنی رمزنگاری‌شده بله (`bale_tunnel.py`):** انتقال داده در شبکه ایزوله با فشرده‌سازی zlib، کدگذاری Base64، چنکینگ و **رمزنگاری متقارن SHA256-CTR + HMAC-SHA256**.
5. **🌐 گیت‌وی هوش مصنوعی اینترنتی (`gateway/ai_gateway.py`):** ساخت خودکار سناریوی اتوماسیون از زبان طبیعی با استفاده از مدل‌های Claude، OpenAI یا Ollama.
6. **📚 حافظه RAG با موتور جستجوی FTS5 (`automation_db.py`):** ذخیره متون و تجربیات به همراه **جستجوی تمام‌متنی SQLite FTS5 و رتبه‌بندی BM25**.
7. **🤖 ربات شنود دوگانه بله (`bale_bot_worker.py`):** پشتیبانی از **Long-Polling مستقیم API بله (HTTP)** و مرورگر (CDP).
8. **🌐 رابط REST API اسکیل‌ها (`web_gui.py`):** مسیرهای `/api/skills` و `/api/knowledge/search` برای وب گرافی.

---

## 🚀 راهنمای استفاده از CLI

دستورات مدیریت ایجنت از طریق `agent_cli.py`:

```bash
# مشاهده لیست اسکیل‌های نصب‌شده
python agent_cli.py list-skills

# اجرای یک اسکیل با آرگومان
python agent_cli.py run-skill demo_recipe --args '{"key":"val"}'

# نصب اسکیل جدید (JSON یا پایتون)
python agent_cli.py install-skill my_skill recipe '{"description":"test","steps":[]}'

# راه اندازی سرور MCP برای Claude Desktop یا Cursor
python agent_cli.py mcp

# جستجو در حافظه RAG محلی (با FTS5)
python agent_cli.py ask "ورود به سامانه"

# کدگذاری و رمزنگاری داده برای ارسال از طریق بله
python agent_cli.py tunnel-encode '{"cmd":"list"}' --key "secret_key"

# بازسازی و رمزگشایی پیام‌های تکه‌تکه‌شده بله
python agent_cli.py tunnel-decode "BALE-TUN|v1|..." --key "secret_key"
```

---

## 🔒 امنیت و شبکه ایزوله

- **اجرا بدون دسترسی ادمین:** بدون نیاز به نصب پایتون، pip یا درایور مرورگر.
- **تأیید اصالت اسکیل‌ها:** جلوگیر از اجرای اسکیل دستکاری‌شده یا غیرمجاز با امضای دیجیتال HMAC-SHA256.
- **رمزنگاری کامل لایه پیام:** تمام پیام‌های متنی در تونل بله با الگوریتم متقارن SHA256-CTR + HMAC رمزنگاری می‌شوند.

---

## 📁 ساختار جدید پروژه

```
├── agent_core.py           # هسته اصلی ایجنت و مدیریت چرخه‌حیات
├── skill_manager.py        # موتور بارگذاری، اعتبارسنجی امضا و مدیریت اسکیل‌ها
├── mcp_adapter.py          # پیاده‌سازی پروتکل MCP over stdio
├── bale_tunnel.py          # پروتکل تونل‌زنی رمزنگاری‌شده (zlib+Base64+Chunking+AE)
├── bale_bot_worker.py      # ربات شنود دوگانه (Bale Bot API HTTP Long-poll / CDP)
├── agent_cli.py            # رابط خط فرمان (CLI) ایجنت
├── gateway/
│   └── ai_gateway.py       # گیت‌وی اتصال به هوش مصنوعی (Claude/OpenAI/Ollama)
├── skills/                 # اسکیل‌های پیش‌فرض
├── skills_user/            # اسکیل‌های نصب‌شده توسط کاربر
├── bale_agent.py           # هسته CDP و استخراج بله
├── page_adapter.js         # اسکریپت خوانش DOM بله
├── automation_engine.py    # موتور اتوماسیون ۲۶+ عملیات
├── automation_db.py        # دیتابیس SQLite، FTS5 RAG و حافظه محلی
├── data_processor.py       # فیلتر و تبدیل داده‌ها
└── web_gui.py              # سرور HTTP، REST API اسکیل‌ها و ویزارد تصویری
```

---

<a name="english-summary"></a>
## English Summary

**Bale Portable AI Agent** is an enterprise-grade offline AI Agent framework supporting Chrome DevTools Protocol (CDP) browser automation, Model Context Protocol (MCP), dynamic Python/JSON skill loading with HMAC signature verification, SQLite FTS5 RAG context memory, AES/SHA256-CTR authenticated encryption over Bale text tunnel, and direct Bale Bot API long polling.
