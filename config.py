# توکن ربات تلگرام (از @BotFather بگیرید)
TELEGRAM_TOKEN = "8615695848:AAFV71ZiRq3UdM2oY_IFMldLf0q72Zd49so"

# لیست APIهای عمومی برای ارسال پیامک
# این APIها را می‌توانید اضافه یا کم کنید
SMS_APIS = [
    {
        "name": "service1",
        "url": "https://api.service1.com/send",
        "params": {"phone": "{phone}", "code": "123456"}
    },
    {
        "name": "service2", 
        "url": "https://api.service2.com/request",
        "params": {"mobile": "{phone}", "type": "verify"}
    },
    {
        "name": "service3",
        "url": "https://api.service3.com/sendSms",
        "params": {"number": "{phone}", "message": "کد تایید"}
    }
]