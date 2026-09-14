# Bale Portable Agent (عامل محلی و قابل‌حمل بله)

عامل محلی، آفلاین و قابل‌حمل برای **اتوماسیون مرورگر** و **استخراج پیام** از نسخه وب پیام‌رسان [بله](https://web.bale.ai) از طریق پروتکل CDP (Chrome DevTools Protocol).

[English Summary](#english-summary) | [راهنمای فارسی وب بله](README.fa.md)

---

## ✨ ویژگی‌های کلیدی

- **کاملاً آفلاین و قابل‌حمل:** بدون نیاز به نصب پایتون، `pip`، درایور مرورگر (Selenium/Playwright)، یا دسترسی ادمین.
- **اجرا روی سیستم‌های سازمانی (Active Directory):** بدون تغییر در ریجستری یا نیاز به سطح دسترسی بالا.
- **رابط کاربری وب فارسی (RTL):** مدیریت بصری اتوماسیون‌ها با ویزارد گام‌به‌گام.
- **موتور اتوماسیون CDP پارامتریک:** تعریف اتوماسیون‌های متنوع با ساختار JSON.
- **دیتابیس محلی SQLite:** ذخیره اتوماسیون‌ها، تنظیمات و لاگ‌های اجرا.
- **استخراج پیام بله:** خوانش آخرین پیام از گفت‌وگوهای شخصی اخیر با خروجی TXT (تقویم شمسی) و JSON.

---

## 🚀 شروع سریع

### ۱. استخراج و آماده‌سازی
فایل ZIP را کاملاً از حالت فشرده خارج کنید. برای ساختن بسته قابل‌حمل:
```bat
make.cmd
```

### ۲. راه‌اندازی مرورگر
```bat
start-browser.cmd
```
یک پنجره Chrome/Edge با پروفایل اختصاصی و پورت اشکال‌زدایی محلی (`127.0.0.1:9222`) باز می‌شود.

### ۳. ورود به بله
در پنجره مرورگر بازشده، به‌صورت دستی وارد حساب بله شوید.

### ۴. استخراج سریع (بدون رابط گرافیکی)
```bat
export-10.cmd
```

### ۵. رابط گرافیکی اتوماسیون
```bat
start-gui.cmd
```
رابط کاربری وب فارسی در آدرس `http://127.0.0.1:8080` باز می‌شود.

---

## 🖥️ رابط کاربری گرافیکی (Web GUI)

رابط گرافیکی فارسی و راست‌به‌چپ شامل بخش‌های زیر است:

### نوار بالا
- نمایش وضعیت اتصال مرورگر (فعال/غیرفعال)

### پنل کناری
- فهرست اتوماسیون‌های ذخیره‌شده
- دکمه ایجاد اتوماسیون جدید
- دکمه راهنمای سریع

### ویرایشگر اتوماسیون
- **عنوان و توضیحات:** نام‌گذاری و شرح اتوماسیون
- **ویزارد بصری:** افزودن گام‌ها با کلیک روی چیپ‌ها (بدون نیاز به نوشتن JSON)
- **ویرایش JSON:** ویرایش مستقیم ساختار JSON برای کاربران پیشرفته
- **جابه‌جایی و حذف گام‌ها:** دکمه‌های بالا/پایین/حذف در هر گام

### نتایج اجرا
- نمایش نتیجه هر گام به‌صورت بصری (موفق/ناموفق)

### تاریخچه (لاگ)
- گزارش تمامی اجراهای قبلی با زمان، وضعیت و جزئیات

---

## ⚙️ عملیات‌های قابل تعریف در اتوماسیون

| عملیات | پارامترها | کاربرد |
|--------|----------|--------|
| `navigate` | `url`, `wait` | هدایت مرورگر به آدرس وب |
| `click` | `selector`, `wait` | کلیک روی دکمه یا لینک با سلکتور CSS |
| `type` | `selector`, `text` | وارد کردن نام کاربری، رمز عبور، یا هر متن |
| `wait` | `seconds` | توقف زمانی (برای بارگذاری صفحه) |
| `wait_for_element` | `selector`, `timeout` | صبر تا ظاهرشدن عنصر خاص در صفحه |
| `evaluate_js` | `code` | اجرای کد JavaScript دلخواه در صفحه |
| `bale_export` | `count`, `timeout` | استخراج آخرین پیام‌های شخصی بله |

### سلکتور CSS چیست؟
سلکتور CSS آدرس یک عنصر HTML در صفحه وب است:
- `#username` → عنصر با شناسه `username`
- `.login-btn` → عنصر با کلاس `login-btn`
- `input[type="password"]` → فیلد رمز عبور
- `button[type="submit"]` → دکمه ارسال فرم

---

## 📋 نمونه اتوماسیون‌ها

### لاگین در یک سامانه وب
```json
[
  {"action": "navigate", "url": "https://portal.example.com/login", "wait": 2},
  {"action": "type", "selector": "#username", "text": "admin"},
  {"action": "type", "selector": "#password", "text": "mypass123"},
  {"action": "click", "selector": "button[type=submit]", "wait": 3},
  {"action": "wait_for_element", "selector": ".dashboard", "timeout": 10}
]
```

### استخراج ۲۰ پیام اخیر بله
```json
[
  {"action": "bale_export", "count": 20, "timeout": 25}
]
```

### ورود به سایت و کلیک روی منو
```json
[
  {"action": "navigate", "url": "https://app.example.com", "wait": 3},
  {"action": "wait_for_element", "selector": "nav.main-menu", "timeout": 10},
  {"action": "click", "selector": "nav.main-menu a:first-child", "wait": 1},
  {"action": "evaluate_js", "code": "document.title"}
]
```

---

## 📁 ساختار پروژه

```
├── bale_agent.py           # منطق اصلی استخراج بله و مدیریت CDP
├── page_adapter.js         # اسکریپت تزریقی جهت خوانش DOM بله
├── automation_engine.py    # موتور اتوماسیون پارامتریک CDP
├── automation_db.py        # مدیریت دیتابیس SQLite (اتوماسیون‌ها و لاگ‌ها)
├── web_gui.py              # سرور HTTP و REST API رابط گرافیکی
├── ui/
│   ├── index.html          # رابط کاربری فارسی RTL
│   ├── style.css           # استایل مدرن
│   └── app.js              # منطق رابط کاربری و ویزارد بصری
├── start-browser.cmd       # راه‌اندازی مرورگر با CDP
├── start-gui.cmd           # راه‌اندازی رابط گرافیکی
├── export-10.cmd           # استخراج سریع ۱۰ پیام
├── run.cmd                 # اجرای دستورات با پایتون پرتابل
├── make.cmd                # بسته‌بندی ZIP قابل‌حمل
├── build_portable.py       # دریافت runtime پایتون (فقط توسعه‌دهنده)
├── runtime/                # پایتون Embeddable x64 (بدون نیاز به نصب)
├── vendor/                 # وابستگی websocket-client (wheel)
├── tests/                  # تست‌های واحد
├── README.fa.md            # مستندات کامل فارسی (استخراج بله)
└── LICENSE                 # مجوز MIT
```

---

## 🔒 امنیت و حریم خصوصی

- اتصال CDP فقط روی `127.0.0.1` (localhost) انجام می‌شود.
- هیچ داده‌ای به سرور خارجی ارسال نمی‌شود.
- از API خصوصی بله، کوکی، رمز عبور یا شنود شبکه استفاده نمی‌شود.
- پروفایل مرورگر مختص برنامه است و با پروفایل شخصی تداخل ندارد.
- خروجی‌ها بدون رمزگذاری ذخیره می‌شوند — مسئولیت نگهداری با کاربر است.

---

## 🛠️ دستورات ترمینال

```bat
:: راه‌اندازی مرورگر
run.cmd launch [--browser PATH] [--port PORT] [--profile PATH]

:: استخراج پیام بله
run.cmd export --count N [--port PORT] [--timeout SEC] [--output DIR]

:: رابط گرافیکی
run.cmd gui

:: بسته‌بندی ZIP
make.cmd
```

---

## 🧪 تست‌ها

```bat
python -m unittest discover -s tests -v
```

---

## 📌 نیازمندی‌های سیستم مقصد

- **سیستم‌عامل:** Windows x64 (تست‌شده روی ویندوز ۱۰ و ۱۱)
- **مرورگر:** Chrome یا Microsoft Edge (از قبل نصب‌شده)
- **دسترسی ادمین:** نیاز نیست
- **اینترنت:** فقط برای دسترسی به `web.bale.ai` یا سایت مقصد اتوماسیون
- **پایتون:** نیاز نیست (runtime پرتابل شامل بسته است)

---

<a name="english-summary"></a>
## English Summary

**Bale Portable Agent** is an offline, zero-dependency Python toolkit for:

1. **Browser Automation via CDP:** Define multi-step automations (navigate, click, type, wait, JS eval) as JSON — managed through a Persian RTL Web GUI with a visual step builder.
2. **Bale Web Message Export:** Extract the latest messages from personal Bale conversations into TXT (Jalali calendar) and JSON files.

### Key Features
- **Portable & Offline:** Runs on air-gapped / Active Directory machines without Python install, pip, admin rights, or browser drivers.
- **Visual Automation Builder:** Web-based Persian GUI at `localhost:8080` with drag-to-reorder steps, chip-based action picker, and inline help.
- **SQLite Database:** Stores automations and execution logs locally.
- **CDP Engine:** Direct WebSocket connection to Chrome/Edge debugging port — no Selenium/Playwright.
- **Dual Output:** `.txt` (Persian/Jalali) and `.json` for Bale exports.

### Quick Start
```bat
start-browser.cmd       :: Launch dedicated browser with CDP
start-gui.cmd           :: Open Web GUI at localhost:8080
export-10.cmd           :: Quick export 10 recent Bale messages
make.cmd                :: Package as portable ZIP
```

---

## License

[MIT License](LICENSE)
