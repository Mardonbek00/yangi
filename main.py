import logging

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters,
)

import config
import handlers_admin as admin_h
import handlers_common as common_h
import handlers_driver as driver_h
import handlers_passenger as passenger_h
from db import Base, SessionLocal, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


# ---------- Matnli xabarlarni yo'naltirish ----------

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    menu_actions = {
        "🚕 Taxi chaqirish": passenger_h.call_taxi_start,
        "🚗 Haydovchi bo'lish": driver_h.become_driver_start,
        "👨‍✈️ Haydovchi paneli": driver_h.driver_panel,
        "📋 Mening buyurtmalarim": common_h.my_orders,
        "🛠 Admin panel": admin_h.admin_panel,
    }
    if text in menu_actions:
        context.user_data["state"] = None
        await menu_actions[text](update, context)
        return

    if text == "⏳ Ariza ko'rib chiqilmoqda":
        await update.message.reply_text("Arizangiz hali ko'rib chiqilmoqda, iltimos kuting.")
        return

    state = context.user_data.get("state")

    if state == "awaiting_comment":
        await passenger_h.receive_comment(update, context)
        return

    if state in ("driver_name", "driver_plate", "driver_model", "driver_color"):
        await driver_h.driver_app_text(update, context)
        return

    if state == "topup_amount":
        await driver_h.topup_amount(update, context)
        return

    if state and state.startswith("admin_"):
        await admin_h.admin_text(update, context)
        return

    await update.message.reply_text("Iltimos, menyudan tanlang.")


async def contact_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await driver_h.driver_app_contact(update, context):
        return
    await passenger_h.receive_phone(update, context)


async def photo_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await driver_h.topup_photo(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    await common_h.start(update, context)


def main():
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN muhit o'zgaruvchisi berilmagan")

    Base.metadata.create_all(engine)

    application = Application.builder().token(config.BOT_TOKEN).build()
    application.bot_data["Session"] = SessionLocal

    # Buyruqlar
    application.add_handler(CommandHandler("start", common_h.start))
    application.add_handler(CommandHandler("cancel", cancel))

    # Yo'lovchi
    application.add_handler(CallbackQueryHandler(passenger_h.choose_direction, pattern=r"^pdir:"))
    application.add_handler(CallbackQueryHandler(passenger_h.skip_comment, pattern=r"^pcomment:skip$"))
    application.add_handler(CallbackQueryHandler(common_h.rate_driver, pattern=r"^rate:"))

    # Haydovchi
    application.add_handler(CallbackQueryHandler(driver_h.driver_app_confirm, pattern=r"^dapp:"))
    application.add_handler(CallbackQueryHandler(driver_h.go_online_start, pattern=r"^dgoonline$"))
    application.add_handler(CallbackQueryHandler(driver_h.go_online_direction, pattern=r"^ddir:"))
    application.add_handler(CallbackQueryHandler(driver_h.depart_button, pattern=r"^ddepart$"))
    application.add_handler(CallbackQueryHandler(driver_h.order_response, pattern=r"^(daccept|dreject):"))
    application.add_handler(CallbackQueryHandler(driver_h.driver_trips, pattern=r"^dtrips$"))
    application.add_handler(CallbackQueryHandler(driver_h.topup_start, pattern=r"^topup:start$"))
    application.add_handler(CallbackQueryHandler(lambda u, c: None, pattern=r"^dbalance$"))

    # Admin
    application.add_handler(CallbackQueryHandler(admin_h.approve_driver, pattern=r"^admin:approve_driver:"))
    application.add_handler(CallbackQueryHandler(admin_h.reject_driver, pattern=r"^admin:reject_driver:"))
    application.add_handler(CallbackQueryHandler(admin_h.approve_topup, pattern=r"^admin:approve_topup:"))
    application.add_handler(CallbackQueryHandler(admin_h.reject_topup, pattern=r"^admin:reject_topup:"))
    application.add_handler(CallbackQueryHandler(admin_h.add_direction_start, pattern=r"^admin:add_direction$"))
    application.add_handler(CallbackQueryHandler(admin_h.set_commission_start, pattern=r"^admin:set_commission$"))
    application.add_handler(CallbackQueryHandler(admin_h.set_card_start, pattern=r"^admin:set_card$"))
    application.add_handler(CallbackQueryHandler(admin_h.stats, pattern=r"^admin:stats$"))

    # Matn / kontakt / rasm
    application.add_handler(MessageHandler(filters.CONTACT, contact_router))
    application.add_handler(MessageHandler(filters.PHOTO, photo_router))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    logger.info("Bot ishga tushdi (polling)")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
