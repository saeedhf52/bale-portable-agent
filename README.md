# Bale Portable Agent (عامل محلی و قابل‌حمل بله)

عامل محلی و قابل‌حمل آفلاین برای استخراج آخرین پیام از گفت‌وگوهای شخصی اخیر در نسخه وب پیام‌رسان بله (`web.bale.ai`).

[English Readme Summary Below](#english-summary) | [راهنمای فارسی کامل](README.fa.md)

---

## ویژگی‌ها و نحوه کار

- **استخراج محلی بدون نیازمندی اضافی:** عدم نیاز به پایتون سیستمی، `pip`، درایور سنگین مرورگر (مثل Selenium یا Playwright)، یا سرویس هوش مصنوعی و API key.
- **ارتباط از طریق Chrome DevTools Protocol (CDP):** اتصال مستقیم و همگام از طریق WebSocket روی پورت محلی (`localhost`).
- **خوانش ساختار رندرشده (DOM):** عدم تماس با APIهای خصوصی بله، عدم شنود شبکه، عدم دسترسی به دیتابیس یا کوکی‌های مرورگر.
- **عدم دستکاری پیام‌ها:** عدم ارسال پیام، عدم حذف، عدم کلیک روی فرم یا کادر ارسال.
- **خروجی دقیق:** خروجی هم‌زمان متنی (TXT با تقویم شمسی و ساعت تهران) و ساختاریافته (JSON).

---

## نحوه استفاده در ویندوز (آفلاین)

1. **دانلود و استخراج:** پوشه برنامه را کاملاً از حالت فشرده (ZIP) خارج کنید.
2. **راه‌اندازی مرورگر اختصاصی:** فایل `start-browser.cmd` را اجرا کنید. یک پنجره Chrome/Edge با پروفایل جداگانه و پورت اشکال‌زدایی local (پورت 9222) باز می‌شود.
3. **ورود دستی:** در پنجره مرورگر بازشده وارد وب بله شوید (`https://web.bale.ai`).
4. **استخراج پیام‌ها:** فایل `export-10.cmd` را اجرا کنید تا ۱۰ پیام اخیر استخراج و در پوشه `output` ذخیره شوند.

---

## دستورات سفارشی (ترمینال)

```bat
:: تغییر تعداد مخاطبان و مسیر خروجی
run.cmd export --count 50 --output "D:\BaleExports"

:: تغییر پورت مرورگر
run.cmd launch --port 9233
run.cmd export --count 10 --port 9233
```

---

## ساختار پروژه

```
├── bale_agent.py       # منطق اصلی استخراج، مدیریت CDP و تولید خروجی
├── page_adapter.js     # اسکریپت تزریقی جهت خوانش عناصر DOM بله
├── build_portable.py   # اسکریپت دریافت پایتون پرتابل و وابستگی‌ها (جهت توسعه/بسته‌بندی)
├── start-browser.cmd   # فایل لانچر مرورگر مخصوص با اشکال‌زدایی CDP
├── export-10.cmd       # فایل اجرای سریع استخراج ۱۰ مخاطب اخیر
├── run.cmd             # فایل اجرای دستورات پایتون پرتابل
├── README.fa.md        # مستندات کامل فارسی
├── tests/              # تست‌های واحد و متدهای تایید
└── LICENSE             # مجوز MIT
```

---

<a name="english-summary"></a>
## English Summary

**Bale Portable Agent** is an offline, zero-dependency Python tool designed to extract the latest messages from recent personal conversations on [Bale Web](https://web.bale.ai) via Chrome DevTools Protocol (CDP).

### Key Highlights
- **Portable & Offline Ready:** Runs on air-gapped/offline machines without installing Python, `pip`, or browser automation frameworks (Playwright/Selenium).
- **Direct CDP via WebSocket:** Connects directly to localhost debugging port (`127.0.0.1:9222`).
- **DOM Reader (`page_adapter.js`):** Reads rendered DOM elements safely without touching private APIs, cookies, or database stores.
- **Formatted Export:** Outputs both `.txt` (with Jalali dates and Tehran time) and structured `.json`.

---

## License

[MIT License](LICENSE)
