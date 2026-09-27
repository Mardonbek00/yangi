import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Render'da avtomatik beriladigan DATABASE_URL (Postgres) yoki lokal SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///taxi_bot.db")

# Vergul bilan ajratilgan admin Telegram ID'lari, masalan: "111111,222222"
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

MAX_SEATS = 4                      # bitta haydovchi bir vaqtda nechta yo'lovchi ola oladi
OFFER_TIMEOUT_SECONDS = 90         # zakazni qabul qilish uchun har bir haydovchiga beriladigan vaqt (1.5 daqiqa)
ORDER_AUTO_CANCEL_SECONDS = 15 * 60  # zakaz avtomatik bekor bo'ladigan umumiy vaqt (15 daqiqa)

DEFAULT_COMMISSION = "2000"        # boshlang'ich komissiya (so'm), admin panel orqali o'zgartiriladi
