# Portable Web Agent — عامل اتوماسیون وب

ابزار آفلاین و قابل‌حمل برای **اتوماسیون مرورگر** از طریق پروتکل CDP (Chrome DevTools Protocol) با رابط گرافیکی فارسی.

[English Summary](#english-summary) | [مستندات استخراج بله](README.fa.md)

---

## ✨ ویژگی‌ها

- **آفلاین و قابل‌حمل:** بدون نیاز به نصب پایتون، `pip`، درایور مرورگر یا دسترسی ادمین
- **سازگار با Active Directory:** اجرا روی سیستم‌های سازمانی بدون تغییر ریجستری
- **رابط گرافیکی فارسی (RTL):** ویزارد بصری ساخت اتوماسیون با فونت وزیرمتن
- **۲۲+ عملیات CDP:** ناوبری، کلیک، تایپ هوشمند، اسکرول، استخراج، کراول و...
- **🔐 ورود هوشمند به سایت:** تشخیص خودکار فرم لاگین (۴۰+ سلکتور)، پر کردن فیلدها، مدیریت کپچا و تأیید ورود
- **تشخیص خودکار کپچا:** شناسایی reCAPTCHA, hCaptcha و کپچای تصویری با توقف خودکار برای دخالت کاربر
- **بررسی خودکار مرورگر:** قبل از هر اجرا وضعیت مرورگر بررسی و در صورت نیاز راه‌اندازی/ری‌استارت می‌شود
- **اتصال مجدد خودکار:** در صورت قطع ارتباط حین اجرا، اتصال مجدد و ادامه اتوماسیون
- **قالب‌های آماده:** لاگین هوشمند، لاگین ساده، لاگین با کپچا، لاگین دو مرحله‌ای، کراول لینک‌ها، پیمایش لیست
- **انتظار دخالت کاربر:** توقف خودکار هنگام برخورد با کپچا یا تأیید دو مرحله‌ای
- **متغیرهای داینامیک:** تعریف و استفاده از متغیرها با `{{نام}}` در فیلدهای متنی
- **حلقه و شرط:** تکرار گام‌ها و اجرای شرطی بر اساس وجود عنصر
- **دیتابیس محلی SQLite:** ذخیره اتوماسیون‌ها و لاگ‌ها
- **استخراج پیام بله:** خوانش آخرین پیام از گفت‌وگوهای شخصی با خروجی TXT/JSON

---

## 🚀 شروع سریع

```bat
start-browser.cmd        :: راه‌اندازی مرورگر با پورت CDP
start-gui.cmd            :: رابط گرافیکی در http://127.0.0.1:8080
export-10.cmd            :: استخراج سریع ۱۰ پیام بله
make.cmd                 :: بسته‌بندی ZIP قابل‌حمل
```

---

## ⚙️ فهرست کامل عملیات‌ها

### ناوبری و تعامل
| عملیات | پارامترها | کاربرد |
|--------|----------|--------|
| `navigate` | `url`, `wait` | هدایت به آدرس وب |
| `click` | `selector`, `wait` | کلیک روی عنصر (با auto-scroll) |
| `scroll` | `selector`, `direction`, `amount` | اسکرول صفحه یا عنصر |
| `scroll_to_bottom` | `selector`, `max_scrolls`, `wait` | پیمایش کامل لیست‌های نامحدود |

### ورودی و فرم
| عملیات | پارامترها | کاربرد |
|--------|----------|--------|
| `type` | `selector`, `text`, `clear` | تایپ متن (پشتیبانی از `{{var}}`) |
| `type_human` | `selector`, `text`, `char_delay` | تایپ کاراکتر به کاراکتر (ضد تشخیص ربات) |
| `select_option` | `selector`, `value` | انتخاب گزینه از منوی کشویی |

### انتظار
| عملیات | پارامترها | کاربرد |
|--------|----------|--------|
| `wait` | `seconds` | توقف زمانی |
| `wait_for_element` | `selector`, `timeout` | صبر تا ظاهرشدن عنصر |
| `wait_element_gone` | `selector`, `timeout` | صبر تا ناپدیدشدن عنصر (لودینگ) |
| `wait_for_human` | `prompt`, `success_selector`, `timeout` | توقف برای کپچا/تأیید دستی |

### استخراج داده
| عملیات | پارامترها | کاربرد |
|--------|----------|--------|
| `extract_text` | `selector`, `attribute`, `store_as` | استخراج متن یک عنصر |
| `extract_list` | `selector`, `attribute`, `store_as` | استخراج لیست از چند عنصر |
| `crawl_links` | `selector`, `store_as` | جمع‌آوری لینک‌های صفحه |
| `scrape_table` | `table_selector`, `include_hidden`, `store_as` | استخراج تک‌صفحه جدول (خودکار/دستی) |
| `scrape_table_pages` | `max_pages`, `table_selector`, `next_selector`, `wait`, `store_as` | پیمایش و استخراج جدول در چند صفحه |
| `screenshot` | — | ذخیره اسکرین‌شات |

### منطق و کنترل جریان
| عملیات | پارامترها | کاربرد |
|--------|----------|--------|
| `set_variable` | `key`, `value` | تعریف متغیر داینامیک |
| `evaluate_js` | `code`, `store_as` | اجرای JavaScript و ذخیره نتیجه |
| `loop` | `count`, `steps`, `break_if`, `continue_if` | تکرار زیرگام‌ها (`{{loop_index}}`) با امکان توقف/رد شدن شرطی |
| `conditional` | `selector`, `conditions`, `logic`, `negate`, `then_steps`, `else_steps` | اجرای شرطی پیشرفته (۱۰ نوع شرط، AND/OR، معکوس) |
| `while_loop` | `conditions`, `selector`, `logic`, `max_iterations`, `steps` | حلقه شرطی — تا زمانی که شرط برقرار است تکرار می‌کند |
| `try_catch` | `try_steps`, `catch_steps`, `finally_steps` | مدیریت خطا — در صورت بروز مشکل، مسیر جایگزین اجرا می‌شود |
| `bale_export` | `count`, `timeout` | استخراج پیام‌های بله |

### 🔐 ورود هوشمند
| عملیات | پارامترها | کاربرد |
|--------|----------|--------|
| `auto_login` | `url`, `username`, `password`, `human_on_captcha`, `timeout`, `success_selector` | تشخیص خودکار فرم ورود + پر کردن + مدیریت کپچا + تأیید |
| `detect_login` | `store_as` | شناسایی فرم ورود بدون وارد کردن اطلاعات |

---

## 🧠 سیستم شرط‌گذاری هوشمند (Flowchart Engine)

### ۱۰ نوع شرط پشتیبانی‌شده
| نوع شرط | پارامترها | عملکرد |
|---------|----------|--------|
| `selector_exists` | `selector` | عنصر CSS در صفحه وجود دارد |
| `selector_visible` | `selector` | عنصر CSS قابل مشاهده است |
| `selector_gone` | `selector` | عنصر CSS در صفحه وجود ندارد |
| `text_contains` | `selector`, `value` | متن عنصر شامل مقدار مشخص‌شده است |
| `text_equals` | `selector`, `value` | متن عنصر دقیقاً برابر مقدار مشخص‌شده است |
| `url_contains` | `value` | آدرس صفحه شامل متن مشخص‌شده است |
| `url_equals` | `value` | آدرس صفحه دقیقاً برابر مقدار است |
| `variable_equals` | `variable`, `value` | مقدار متغیر برابر value است |
| `variable_set` | `variable` | متغیر مقداردهی شده و خالی نیست |
| `js_expression` | `code` | عبارت JavaScript نتیجه truthy برمی‌گرداند |

### نمونه شرط ترکیبی پیشرفته
```json
{
  "action": "conditional",
  "conditions": [
    {"type": "url_contains", "value": "/dashboard"},
    {"type": "selector_exists", "selector": ".welcome-msg"}
  ],
  "logic": "and",
  "negate": false,
  "then_steps": [
    {"action": "extract_text", "selector": "h1", "store_as": "title"}
  ],
  "else_steps": [
    {"action": "screenshot"},
    {"action": "wait_for_human", "prompt": "ورود ناموفق بود.", "success_selector": ".dashboard", "timeout": 120}
  ]
}
```

### نمونه حلقه شرطی (while)
```json
{
  "action": "while_loop",
  "conditions": [{"type": "selector_exists", "selector": ".load-more:not([disabled])"}],
  "max_iterations": 50,
  "steps": [
    {"action": "click", "selector": ".load-more", "wait": 2},
    {"action": "extract_list", "selector": ".item", "store_as": "items"}
  ]
}
```

### نمونه مدیریت خطا (try/catch)
```json
{
  "action": "try_catch",
  "try_steps": [
    {"action": "click", "selector": "#submit", "wait": 2},
    {"action": "wait_for_element", "selector": ".success", "timeout": 10}
  ],
  "catch_steps": [
    {"action": "screenshot"},
    {"action": "wait_for_human", "prompt": "خطا رخ داد.", "success_selector": "body", "timeout": 300}
  ],
  "finally_steps": [
    {"action": "screenshot"}
  ]
}
```

---

## 📦 قالب‌های آماده

### 🔐 ورود هوشمند (تشخیص خودکار فرم)
```json
[
  {"action": "auto_login", "url": "https://example.com/login",
   "username": "admin", "password": "mypass",
   "human_on_captcha": true, "timeout": 30}
]
```
> فرم ورود را خودکار شناسایی می‌کند (۴۰+ سلکتور فارسی و انگلیسی)، فیلدها را پر می‌کند، کپچا را تشخیص می‌دهد و در صورت نیاز منتظر کاربر می‌ماند.

### 🔑 ورود دو مرحله‌ای (OTP)
```json
[
  {"action": "auto_login", "url": "https://example.com/login",
   "username": "admin", "password": "mypass",
   "human_on_captcha": true, "timeout": 30},
  {"action": "wait_for_human",
   "prompt": "کد تأیید پیامکی یا OTP را وارد کنید.",
   "success_selector": ".dashboard", "timeout": 180}
]
```

### 🔍 شناسایی فرم ورود (بدون لاگین)
```json
[
  {"action": "navigate", "url": "https://example.com/login", "wait": 3},
  {"action": "detect_login", "store_as": "login_info"}
]
```

### ورود ساده به سایت
```json
[
  {"action": "navigate", "url": "https://example.com/login", "wait": 2},
  {"action": "type", "selector": "#username", "text": "admin"},
  {"action": "type", "selector": "#password", "text": "mypass"},
  {"action": "click", "selector": "button[type=submit]", "wait": 3},
  {"action": "wait_for_element", "selector": ".dashboard", "timeout": 10}
]
```

### ورود با کپچا (انتظار دخالت کاربر)
```json
[
  {"action": "navigate", "url": "https://example.com/login", "wait": 2},
  {"action": "type", "selector": "#username", "text": "admin"},
  {"action": "type", "selector": "#password", "text": "mypass"},
  {"action": "wait_for_human", "prompt": "کپچا را حل کنید و دکمه ورود را بزنید.",
   "success_selector": ".dashboard", "timeout": 120}
]
```

### پر کردن فرم با متغیرهای داینامیک
```json
[
  {"action": "set_variable", "key": "user", "value": "admin"},
  {"action": "set_variable", "key": "pass", "value": "123456"},
  {"action": "navigate", "url": "https://example.com/form", "wait": 2},
  {"action": "type", "selector": "#username", "text": "{{user}}"},
  {"action": "type_human", "selector": "#password", "text": "{{pass}}", "char_delay": 0.1},
  {"action": "click", "selector": "button[type=submit]", "wait": 2}
]
```

### پیمایش لیست و استخراج آیتم‌ها
```json
[
  {"action": "navigate", "url": "https://example.com/list", "wait": 3},
  {"action": "scroll_to_bottom", "max_scrolls": 15, "wait": 1},
  {"action": "extract_list", "selector": ".list-item", "store_as": "items"}
]
```

### جمع‌آوری لینک‌های صفحه
```json
[
  {"action": "navigate", "url": "https://example.com", "wait": 3},
  {"action": "crawl_links", "selector": "a[href]", "store_as": "links"}
]
```

---

## 📁 ساختار پروژه

```
├── bale_agent.py           # هسته CDP و استخراج بله
├── page_adapter.js         # اسکریپت خوانش DOM بله
├── automation_engine.py    # موتور اتوماسیون ۲۲+ عملیات + ورود هوشمند + قالب‌های آماده
├── automation_db.py        # دیتابیس SQLite
├── data_processor.py       # پردازش خروجی‌ها، فیلتر، تبدیل CSV
├── web_gui.py              # سرور HTTP و REST API
├── ui/
│   ├── index.html          # رابط فارسی RTL
│   ├── style.css           # طراحی مدرن
│   ├── app.js              # ویزارد بصری و منطق UI
│   └── fonts/              # فونت وزیرمتن (آفلاین)
├── start-browser.cmd       :: مرورگر CDP
├── start-gui.cmd           :: رابط گرافیکی
├── export-10.cmd           :: استخراج سریع
├── run.cmd                 :: اجرای دستورات
├── make.cmd                :: بسته‌بندی ZIP
├── runtime/                # پایتون Embeddable x64
├── vendor/                 # websocket-client wheel
├── tests/                  # تست‌ها
└── LICENSE                 # MIT
```

---

## 🔒 امنیت

- اتصال CDP فقط روی `127.0.0.1`
- هیچ داده‌ای به سرور خارجی ارسال نمی‌شود
- پروفایل مرورگر مختص برنامه
- خروجی‌ها بدون رمزگذاری — مسئولیت نگهداری با کاربر

---

## 📌 نیازمندی‌ها

- Windows x64 (تست‌شده: ویندوز ۱۰/۱۱)
- Chrome یا Edge نصب‌شده
- بدون نیاز به دسترسی ادمین یا نصب پایتون

---

<a name="english-summary"></a>
## English Summary

**Portable Web Agent** is an offline, zero-dependency CDP browser automation toolkit with a Persian RTL Web GUI.

### Features
- **22+ CDP Actions:** navigate, click, type (normal & human-like), scroll, wait, extract text/lists, crawl links, screenshot, JS eval, loops, conditionals
- **🔐 Smart Login:** Auto-detect login forms (40+ selectors for Persian & English sites), fill credentials, detect CAPTCHA, verify success/error
- **Auto Browser Management:** Pre-flight browser check before every run — auto-launch or restart if dead/stuck
- **Auto-Reconnect:** If connection drops mid-run, reconnects and continues
- **Human-in-the-loop:** `wait_for_human` pauses for CAPTCHA/2FA with on-page banner
- **Dynamic Variables:** `set_variable` + `{{var}}` templates in text fields
- **Built-in Templates:** Smart login, basic login, CAPTCHA login, 2FA login, form fill, list crawl, link crawl, Bale export
- **Portable:** Runs on air-gapped Active Directory machines — no Python install, pip, admin rights, or browser drivers
- **SQLite Storage:** Automations and execution logs stored locally
- **Visual Builder:** Chip-based step picker, drag-to-reorder, duplicate, inline editing

### Quick Start
```bat
start-browser.cmd       :: Launch Chrome/Edge with CDP
start-gui.cmd           :: Web GUI at localhost:8080
export-10.cmd           :: Quick Bale message export
make.cmd                :: Package as portable ZIP
```

---

## License

[MIT](LICENSE)
