from datetime import datetime

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

import config
from keyboards import (
    admin_driver_review_kb, contact_request_kb, directions_kb,
    driver_application_confirm_kb, driver_panel_kb, main_menu,
)
from matching import depart_driver, accept_order, offer_to_driver_queue, try_assign_order
from models import Direction, Driver, Order, Topup
from utils import driver_card_text, fmt_money, get_card_info, get_or_create_user


# ---------- Haydovchi bo'lish arizasi ----------

async def become_driver_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = context.bot_data["Session"]()
    try:
        existing = session.get(Driver, update.effective_user.id)
    finally:
        session.close()

    if existing and existing.status in ("pending", "approved"):
        await update.message.reply_text("Sizning arizangiz allaqachon topshirilgan yoki tasdiqlangan.")
        return

    context.user_data["state"] = "driver_name"
    context.user_data["driver_app"] = {}
    await update.message.reply_text("Ism-familiyangizni kiriting:", reply_markup=ReplyKeyboardRemove())


async def driver_app_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """True qaytarsa — xabar shu handlerda ishlov berildi."""
    state = context.user_data.get("state")
    app = context.user_data.get("driver_app", {})

    if state == "driver_name":
        app["full_name"] = update.message.text.strip()
        context.user_data["state"] = "driver_phone"
        await update.message.reply_text("Telefon raqamingizni ulashing:", reply_markup=contact_request_kb())
        return True

    if state == "driver_plate":
        app["car_plate"] = update.message.text.strip()
        context.user_data["state"] = "driver_model"
        await update.message.reply_text("Avtomobil rusumini kiriting (masalan: Nexia 3):")
        return True

    if state == "driver_model":
        app["car_model"] = update.message.text.strip()
        context.user_data["state"] = "driver_color"
        await update.message.reply_text("Avtomobil rangini kiriting:")
        return True

    if state == "driver_color":
        app["car_color"] = update.message.text.strip()
        context.user_data["state"] = None
        text = (
            "Ma'lumotlaringizni tekshiring:\n\n"
            f"Ism: {app['full_name']}\n"
            f"Telefon: {app['phone']}\n"
            f"Davlat raqami: {app['car_plate']}\n"
            f"Rusumi: {app['car_model']}\n"
            f"Rangi: {app['car_color']}\n\n"
            "Adminга yuborilsinmi?"
        )
        await update.message.reply_text(text, reply_markup=driver_application_confirm_kb())
        return True

    return False


async def driver_app_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if context.user_data.get("state") != "driver_phone":
        return False
    app = context.user_data.setdefault("driver_app", {})
    app["phone"] = update.message.contact.phone_number
    context.user_data["state"] = "driver_plate"
    await update.message.reply_text("Avtomobil davlat raqamini kiriting:", reply_markup=ReplyKeyboardRemove())
    return True


async def driver_app_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data.split(":")[1]
    app = context.user_data.pop("driver_app", None)

    if action == "cancel" or not app:
        await query.edit_message_text("Ariza bekor qilindi.")
        return

    user = update.effective_user
    session = context.bot_data["Session"]()
    try:
        get_or_create_user(session, user)
        driver = session.get(Driver, user.id)
        if driver is None:
            driver = Driver(user_id=user.id)
            session.add(driver)
        driver.full_name = app["full_name"]
        driver.phone = app["phone"]
        driver.car_plate = app["car_plate"]
        driver.car_model = app["car_model"]
        driver.car_color = app["car_color"]
        driver.status = "pending"
        session.commit()
        review_text = (
            "🆕 Yangi haydovchi arizasi:\n\n"
            f"Ism: {driver.full_name}\n"
            f"Telefon: {driver.phone}\n"
            f"Mashina: {driver.car_model}, {driver.car_color}, {driver.car_plate}\n"
            f"Telegram ID: {driver.user_id}"
        )
    finally:
        session.close()

    await query.edit_message_text("✅ Arizangiz adminga yuborildi. Tasdiqlangach xabar beramiz.")

    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, review_text, reply_markup=admin_driver_review_kb(user.id))
        except Exception:
            pass


# ---------- Haydovchi paneli ----------

async def driver_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = context.bot_data["Session"]()
    try:
        driver = session.get(Driver, update.effective_user.id)
        if driver is None or driver.status != "approved":
            await update.message.reply_text("Siz hali tasdiqlangan haydovchi emassiz.")
            return
        text = f"{driver_card_text(driver)}\n\n💰 Balans: {fmt_money(driver.balance)}"
        kb = driver_panel_kb(driver)
    finally:
        session.close()

    await update.message.reply_text(text, reply_markup=kb)


async def go_online_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    session = context.bot_data["Session"]()
    try:
        driver = session.get(Driver, update.effective_user.id)
        if driver.balance <= 0:
            await query.message.reply_text("❌ Balansingiz yetarli emas. Avval balansni to'ldiring.")
            return
        directions = session.query(Direction).filter_by(active=True).all()
    finally:
        session.close()

    if not directions:
        await query.message.reply_text("Hozircha yo'nalishlar qo'shilmagan.")
        return

    await query.message.reply_text("Yo'nalishni tanlang:", reply_markup=directions_kb(directions, "ddir"))


async def go_online_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    direction_id = int(query.data.split(":")[1])

    session = context.bot_data["Session"]()
    try:
        driver = session.get(Driver, update.effective_user.id)
        driver.is_online = True
        driver.direction_id = direction_id
        driver.queue_joined_at = datetime.utcnow()
        driver.seats_taken = 0
        session.commit()
        direction_name = driver.direction.name
    finally:
        session.close()

    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"🟢 Siz liniyaga chiqdingiz: {direction_name}. Navbatingiz saqlandi.")
    await offer_to_driver_queue(context, driver)


async def depart_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    session = context.bot_data["Session"]()
    try:
        driver = session.get(Driver, update.effective_user.id)
        await depart_driver(context, driver, session)
    finally:
        session.close()
    await query.edit_message_text("🔴 Siz liniyadan chiqdingiz.")


async def order_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, order_id = query.data.split(":")
    order_id = int(order_id)

    session = context.bot_data["Session"]()
    try:
        order = session.get(Order, order_id)
        driver = session.get(Driver, update.effective_user.id)

        if order is None or order.status != "offered" or order.driver_id != driver.user_id:
            await query.edit_message_text("Bu buyurtma allaqachon boshqa haydovchiga o'tgan yoki bekor bo'lgan.")
            return

        if action == "daccept":
            await accept_order(context, order, driver, session)
            await query.edit_message_text("✅ Siz buyurtmani qabul qildingiz.")
        else:
            from models import OrderRejection
            session.add(OrderRejection(order_id=order.id, driver_id=driver.user_id))
            order.status = "waiting"
            order.driver_id = None
            session.commit()
            await query.edit_message_text("❌ Siz buyurtmani rad etdingiz.")
    finally:
        session.close()

    if action == "dreject":
        await try_assign_order(context, order_id)


async def driver_trips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    session = context.bot_data["Session"]()
    try:
        orders = (
            session.query(Order)
            .filter_by(driver_id=update.effective_user.id, status="completed")
            .order_by(Order.created_at.desc())
            .limit(10)
            .all()
        )
        if not orders:
            await query.message.reply_text("Hali safarlar yo'q.")
            return
        lines = []
        for o in orders:
            date = o.created_at.strftime("%d.%m.%Y %H:%M")
            rating = f"{o.rating}⭐" if o.rating else "baholanmagan"
            lines.append(f"№{o.id} | {date} | {o.direction.name} | {rating}")
        await query.message.reply_text("\n".join(lines))
    finally:
        session.close()


# ---------- Balansni to'ldirish ----------

async def topup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    session = context.bot_data["Session"]()
    try:
        number, holder = get_card_info(session)
    finally:
        session.close()

    if not number:
        await query.message.reply_text("Admin hali karta ma'lumotlarini kiritmagan. Keyinroq urinib ko'ring.")
        return

    context.user_data["state"] = "topup_photo"
    await query.message.reply_text(
        f"💳 Karta: {number}\n👤 Egasi: {holder}\n\n"
        "To'lovni amalga oshirib, chek/skrinshot rasmini yuboring."
    )


async def topup_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if context.user_data.get("state") != "topup_photo":
        return False
    file_id = update.message.photo[-1].file_id
    context.user_data["topup_file_id"] = file_id
    context.user_data["state"] = "topup_amount"
    await update.message.reply_text("Necha so'm to'lov qildingiz? Summani raqamda kiriting:")
    return True


async def topup_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if context.user_data.get("state") != "topup_amount":
        return False
    raw = update.message.text.strip().replace(" ", "")
    if not raw.isdigit():
        await update.message.reply_text("Iltimos, summani faqat raqam bilan kiriting.")
        return True

    amount = int(raw)
    file_id = context.user_data.pop("topup_file_id")
    context.user_data["state"] = None
    user = update.effective_user

    session = context.bot_data["Session"]()
    try:
        get_or_create_user(session, user)
        topup = Topup(user_id=user.id, amount=amount, screenshot_file_id=file_id)
        session.add(topup)
        session.commit()
        topup_id = topup.id
    finally:
        session.close()

    await update.message.reply_text("✅ So'rovingiz adminga yuborildi. Tasdiqlangach balansingiz to'ldiriladi.")

    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_photo(
                admin_id, file_id,
                caption=f"💳 Balans to'ldirish so'rovi\nFoydalanuvchi ID: {user.id}\nSumma: {fmt_money(amount)}",
                reply_markup=admin_topup_kb(topup_id),
            )
        except Exception:
            pass
    return True


def admin_topup_kb(topup_id: int):
    from keyboards import admin_topup_review_kb
    return admin_topup_review_kb(topup_id)
