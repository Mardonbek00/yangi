from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from keyboards import admin_panel_kb
from models import Direction, Driver, Order, Topup
from utils import fmt_money, get_commission, is_admin, set_setting


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["state"] = None
    await update.message.reply_text("🛠 Admin panel:", reply_markup=admin_panel_kb())


async def approve_driver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    _, _, driver_id = query.data.split(":")
    driver_id = int(driver_id)

    session = context.bot_data["Session"]()
    try:
        driver = session.get(Driver, driver_id)
        driver.status = "approved"
        session.commit()
    finally:
        session.close()

    await query.edit_message_text(query.message.text + "\n\n✅ TASDIQLANDI")
    try:
        await context.bot.send_message(driver_id, "🎉 Tabriklaymiz! Sizning haydovchilik arizangiz tasdiqlandi.")
    except Exception:
        pass


async def reject_driver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    _, _, driver_id = query.data.split(":")
    driver_id = int(driver_id)

    session = context.bot_data["Session"]()
    try:
        driver = session.get(Driver, driver_id)
        driver.status = "rejected"
        session.commit()
    finally:
        session.close()

    await query.edit_message_text(query.message.text + "\n\n❌ RAD ETILDI")
    try:
        await context.bot.send_message(driver_id, "😔 Afsuski, haydovchilik arizangiz rad etildi.")
    except Exception:
        pass


async def approve_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    _, _, topup_id = query.data.split(":")
    topup_id = int(topup_id)

    session = context.bot_data["Session"]()
    try:
        topup = session.get(Topup, topup_id)
        if topup.status != "pending":
            return
        topup.status = "approved"
        driver = session.get(Driver, topup.user_id)
        if driver:
            driver.balance += topup.amount
        session.commit()
        user_id, amount = topup.user_id, topup.amount
    finally:
        session.close()

    await query.edit_message_caption(caption=query.message.caption + "\n\n✅ TASDIQLANDI")
    try:
        await context.bot.send_message(user_id, f"✅ Balansingiz {fmt_money(amount)} ga to'ldirildi.")
    except Exception:
        pass


async def reject_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    _, _, topup_id = query.data.split(":")
    topup_id = int(topup_id)

    session = context.bot_data["Session"]()
    try:
        topup = session.get(Topup, topup_id)
        if topup.status != "pending":
            return
        topup.status = "rejected"
        session.commit()
        user_id = topup.user_id
    finally:
        session.close()

    await query.edit_message_caption(caption=query.message.caption + "\n\n❌ RAD ETILDI")
    try:
        await context.bot.send_message(user_id, "❌ Balans to'ldirish so'rovingiz rad etildi.")
    except Exception:
        pass


async def add_direction_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    context.user_data["state"] = "admin_add_direction"
    await query.message.reply_text("Yangi yo'nalish nomini kiriting:")


async def set_commission_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    context.user_data["state"] = "admin_set_commission"
    await query.message.reply_text("Har bir yo'lovchi uchun komissiya summasini kiriting (so'm):")


async def set_card_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    context.user_data["state"] = "admin_set_card_number"
    await query.message.reply_text("Karta raqamini kiriting:")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    session = context.bot_data["Session"]()
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = today_start.replace(day=1)

        today_count = session.query(Order).filter(Order.created_at >= today_start).count()
        month_count = session.query(Order).filter(Order.created_at >= month_start).count()
        active_drivers = session.query(Driver).filter_by(is_online=True).count()
        approved_drivers = session.query(Driver).filter_by(status="approved").count()
        pending_topups = session.query(Topup).filter_by(status="pending").count()

        text = (
            "📊 Statistika\n\n"
            f"Bugungi buyurtmalar: {today_count}\n"
            f"Shu oydagi buyurtmalar: {month_count}\n"
            f"Hozir liniyada: {active_drivers}\n"
            f"Jami tasdiqlangan haydovchilar: {approved_drivers}\n"
            f"Kutilayotgan balans so'rovlari: {pending_topups}"
        )
    finally:
        session.close()

    await query.message.reply_text(text)


async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Admin panel matnli kirishlarini boshqaradi. True qaytarsa — ishlov berilgan."""
    state = context.user_data.get("state")
    if state not in ("admin_add_direction", "admin_set_commission", "admin_set_card_number", "admin_set_card_holder"):
        return False
    if not is_admin(update.effective_user.id):
        return False

    text = update.message.text.strip()
    session = context.bot_data["Session"]()
    try:
        if state == "admin_add_direction":
            session.add(Direction(name=text))
            session.commit()
            context.user_data["state"] = None
            await update.message.reply_text(f"✅ Yo'nalish qo'shildi: {text}")

        elif state == "admin_set_commission":
            if not text.isdigit():
                await update.message.reply_text("Iltimos, faqat raqam kiriting.")
                return True
            set_setting(session, "commission_amount", text)
            context.user_data["state"] = None
            await update.message.reply_text(f"✅ Komissiya {fmt_money(int(text))} qilib belgilandi.")

        elif state == "admin_set_card_number":
            context.user_data["card_number"] = text
            context.user_data["state"] = "admin_set_card_holder"
            await update.message.reply_text("Karta egasining ism-familiyasini kiriting:")

        elif state == "admin_set_card_holder":
            number = context.user_data.pop("card_number")
            set_setting(session, "card_number", number)
            set_setting(session, "card_holder", text)
            context.user_data["state"] = None
            await update.message.reply_text("✅ Karta ma'lumotlari yangilandi.")
    finally:
        session.close()

    return True
