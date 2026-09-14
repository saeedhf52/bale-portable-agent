# Portable Web Agent — عامل اتوماسیون وب

ابزار آفلاین و قابل‌حمل برای **اتوماسیون مرورگر** از طریق پروتکل CDP (Chrome DevTools Protocol) با رابط گرافیکی فارسی.

[English Summary](#english-summary) | [مستندات استخراج بله](README.fa.md)

---

## ✨ ویژگی‌ها

- **آفلاین و قابل‌حمل:** بدون نیاز به نصب پایتون، `pip`، درایور مرورگر یا دسترسی ادمین
- **سازگار با Active Directory:** اجرا روی سیستم‌های سازمانی بدون تغییر ریجستری
- **رابط گرافیکی فارسی (RTL):** ویزارد بصری ساخت اتوماسیون با فونت وزیرمتن
- **۲۰+ عملیات CDP:** ناوبری، کلیک، تایپ هوشمند، اسکرول، استخراج، کراول و...
- **قالب‌های آماده:** لاگین عمومی، لاگین با کپچا، کراول لینک‌ها، پیمایش لیست، پر کردن فرم داینامیک
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
| `screenshot` | — | ذخیره اسکرین‌شات |

### منطق و کنترل
| عملیات | پارامترها | کاربرد |
|--------|----------|--------|
| `set_variable` | `key`, `value` | تعریف متغیر داینامیک |
| `evaluate_js` | `code`, `store_as` | اجرای JavaScript و ذخیره نتیجه |
| `loop` | `count`, `steps` | تکرار زیرگام‌ها (`{{loop_index}}`) |
| `conditional` | `selector`, `then_steps`, `else_steps` | اجرای شرطی |
| `bale_export` | `count`, `timeout` | استخراج پیام‌های بله |

---

## 📦 قالب‌های آماده

### ورود به سایت (عمومی)
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
├── automation_engine.py    # موتور اتوماسیون ۲۰+ عملیات + قالب‌های آماده
├── automation_db.py        # دیتابیس SQLite
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
- **20+ CDP Actions:** navigate, click, type (normal & human-like), scroll, wait, extract text/lists, crawl links, screenshot, JS eval, loops, conditionals
- **Human-in-the-loop:** `wait_for_human` pauses for CAPTCHA/2FA with on-page banner
- **Dynamic Variables:** `set_variable` + `{{var}}` templates in text fields
- **Built-in Templates:** Login (basic & CAPTCHA), form fill, list crawl, link crawl, Bale export
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
