from telegram import Update
from telegram.ext import ContextTypes

from keyboards import contact_request_kb, directions_kb, main_menu, skip_comment_kb
from matching import try_assign_order
from models import Direction, Driver, Order
from utils import get_or_create_user


async def call_taxi_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = context.bot_data["Session"]()
    try:
        directions = session.query(Direction).filter_by(active=True).all()
    finally:
        session.close()

    if not directions:
        await update.message.reply_text("Hozircha yo'nalishlar qo'shilmagan. Iltimos, keyinroq urinib ko'ring.")
        return

    context.user_data["state"] = None
    await update.message.reply_text("Yo'nalishni tanlang:", reply_markup=directions_kb(directions, "pdir"))


async def choose_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    direction_id = int(query.data.split(":")[1])
    context.user_data["order"] = {"direction_id": direction_id}
    context.user_data["state"] = "awaiting_phone"

    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(
        "Telefon raqamingizni ulashing:",
        reply_markup=contact_request_kb(),
    )


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "awaiting_phone":
        return  # boshqa oqim (masalan haydovchi arizasi) ushlaydi
    phone = update.message.contact.phone_number
    context.user_data["order"]["phone"] = phone
    context.user_data["state"] = "awaiting_comment"

    from telegram import ReplyKeyboardRemove
    await update.message.reply_text("Raqam qabul qilindi.", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(
        "Izoh qo'shmoqchimisiz? Yozing yoki o'tkazib yuboring.",
        reply_markup=skip_comment_kb(),
    )


async def receive_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "awaiting_comment":
        return
    await _create_order(update, context, comment=update.message.text)


async def skip_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if context.user_data.get("state") != "awaiting_comment":
        return
    await query.edit_message_reply_markup(reply_markup=None)
    await _create_order(update, context, comment=None, from_callback=True)


async def _create_order(update: Update, context: ContextTypes.DEFAULT_TYPE, comment, from_callback=False):
    data = context.user_data.pop("order")
    context.user_data["state"] = None
    user = update.effective_user

    session = context.bot_data["Session"]()
    try:
        get_or_create_user(session, user)
        order = Order(
            passenger_id=user.id,
            direction_id=data["direction_id"],
            phone=data["phone"],
            comment=comment,
            status="waiting",
        )
        session.add(order)
        session.commit()
        order_id = order.id
        driver_status = None
        driver = session.get(Driver, user.id)
        driver_status = driver.status if driver else None
    finally:
        session.close()

    reply_target = update.callback_query.message if from_callback else update.message
    await reply_target.reply_text(
        "✅ Buyurtmangiz qabul qilindi! Haydovchi topilishi bilan sizga xabar beramiz.",
        reply_markup=main_menu(user.id, driver_status),
    )

    await try_assign_order(context, order_id)
