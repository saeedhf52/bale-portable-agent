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
|  |  - Dynamic Skill Engine (اسکیل‌های JSON/Python)   |  |       |  |  - Scenario Generator & Code Synthesizer        |  |
|  |  - Local RAG Memory (SQLite Knowledge Base)     |  |       |  |  - Vector RAG Knowledge Base                   |  |
|  |  - MCP Server (Model Context Protocol)          |  |       |  |  - MCP Tool Registry                           |  |
|  +-----------------------+-------------------------+  |       |  +-----------------------+-------------------------+  |
|                          |                            |       |                          |                            |
|                          v                            |       |                          v                            |
|  +-------------------------------------------------+  |       |  +-------------------------------------------------+  |
|  |          Bale Worker Bot (ربات محلی)             |  |       |  |          Bale Gateway Bot (ربات گیت‌وی)          |  |
|  |  - Protocol Serializer (Chunking/Base64/Crypto) |  |       |  |  - Protocol Deserializer & Command Handler         |  |
|  +-----------------------+-------------------------+  |       |  +-----------------------+-------------------------+  |
+--------------------------|----------------------------+       +--------------------------|----------------------------+
                           |                                                               |
                           +=================== کانال متنی بله ============================+
                                 (Bale Messenger Protocol / Text Tunnel)
```

---

## ✨ ویژگی‌های جدید و کلیدی

1. **🧠 هسته ماژولار ایجنت (`agent_core.py`):** مدیریت چرخه‌حیات ایجنت، اجرای اسکیل‌ها و مدیریت حالت به صورت سرویس/کنسول.
2. **🔌 سیستم اسکیل‌های داینامیک (`skill_manager.py`):** تعریف و نصب اسکیل‌ها به صورت سناریوی JSON یا ماژول پایتون.
3. **🤖 پروتکل MCP اختصاصی (`mcp_adapter.py`):** پیاده‌سازی استاندارد Model Context Protocol جهت اتصال ابزارهای ایجنت به Claude Desktop و Cursor.
4. **📡 تونل متنی بله (`bale_tunnel.py`):** انتقال داده در شبکه ایزوله از طریق پیام‌های متنی بله با فشرده‌سازی zlib، کدگذاری Base64، تکه‌تکه‌سازی (Chunking) و هش SHA-256.
5. **🌐 گیت‌وی هوش مصنوعی اینترنتی (`gateway/ai_gateway.py`):** ساخت خودکار سناریوی اتوماسیون از زبان طبیعی با استفاده از مدل‌های Claude، OpenAI یا Ollama.
6. **📚 حافظه RAG محلی (`automation_db.py`):** ذخیره متون، مستندات و تجربیات اجرا به صورت محلی جهت رشد و بلوغ مداوم ایجنت.

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

# جستجو در حافظه RAG محلی
python agent_cli.py ask "ورود به سامانه"

# کدگذاری داده برای ارسال از طریق پیام‌رسان بله
python agent_cli.py tunnel-encode '{"cmd":"list"}' --key "secret"

# بازسازی پیام‌های تکه‌تکه‌شده بله
python agent_cli.py tunnel-decode "BALE-TUN|v1|..." --key "secret"
```

---

## 🔒 امنیت و شبکه ایزوله

- **اجرا بدون دسترسی ادمین:** بدون نیاز به نصب پایتون، pip یا درایور مرورگر.
- **ارتباط ایزوله:** در شبکه‌های بدون اینترنت، داده‌ها فشرده و به تکه‌های متنی تبدیل می‌شوند تا روی بستر پیام‌رسان منتقل گردند.
- **رمزنگاری اختیاری:** امکان ارائه کلید متقارن (`key`) جهت رمزنگاری داده‌ها قبل از تبدیل به فریم‌های متنی.

---

## 📁 ساختار جدید پروژه

```
├── agent_core.py           # هسته اصلی ایجنت و مدیریت چرخه‌حیات
├── skill_manager.py        # موتور بارگذاری و مدیریت اسکیل‌ها
├── mcp_adapter.py          # پیاده‌سازی پروتکل MCP over stdio
├── bale_tunnel.py          # پروتکل تونل‌زنی متنی بله (zlib+Base64+Chunking)
├── bale_bot_worker.py      # ربات شنود و اجرای دستورات بله
├── agent_cli.py            # رابط خط فرمان (CLI) ایجنت
├── gateway/
│   └── ai_gateway.py       # گیت‌وی اتصال به هوش مصنوعی (Claude/OpenAI/Ollama)
├── skills/                 # اسکیل‌های پیش‌فرض
├── skills_user/            # اسکیل‌های نصب‌شده توسط کاربر
├── bale_agent.py           # هسته CDP و استخراج بله
├── page_adapter.js         # اسکریپت خوانش DOM بله
├── automation_engine.py    # موتور اتوماسیون ۲۶+ عملیات
├── automation_db.py        # دیتابیس SQLite و RAG محلی
├── data_processor.py       # فیلتر و تبدیل داده‌ها
└── web_gui.py              # سرور HTTP و ویزارد تصویری
```

---

<a name="english-summary"></a>
## English Summary

**Bale Portable AI Agent** is an enterprise-grade offline AI Agent framework supporting Chrome DevTools Protocol (CDP) browser automation, Model Context Protocol (MCP), dynamic Python/JSON skill loading, local RAG context memory, and a text-based communication tunnel over Bale messenger for air-gapped environments.
