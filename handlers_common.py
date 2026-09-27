from telegram import Update
from telegram.ext import ContextTypes

from keyboards import main_menu
from models import Driver, Order
from utils import get_or_create_user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = context.bot_data["Session"]()
    try:
        get_or_create_user(session, update.effective_user)
        driver = session.get(Driver, update.effective_user.id)
        status = driver.status if driver else None
    finally:
        session.close()

    context.user_data.clear()
    await update.message.reply_text(
        "Assalomu alaykum! O'qchi-Yaypan taxi botiga xush kelibsiz.",
        reply_markup=main_menu(update.effective_user.id, status),
    )


async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = context.bot_data["Session"]()
    try:
        orders = (
            session.query(Order)
            .filter_by(passenger_id=update.effective_user.id)
            .order_by(Order.created_at.desc())
            .limit(10)
            .all()
        )
        if not orders:
            await update.message.reply_text("Sizda hali buyurtmalar yo'q.")
            return

        status_names = {
            "waiting": "⏳ Kutilmoqda",
            "offered": "⏳ Kutilmoqda",
            "accepted": "🚗 Yo'lda",
            "completed": "✅ Yakunlandi",
            "cancelled": "❌ Bekor qilindi",
        }
        lines = []
        for o in orders:
            date = o.created_at.strftime("%d.%m.%Y %H:%M")
            lines.append(
                f"№{o.id} | {date}\n"
                f"Yo'nalish: {o.direction.name}\n"
                f"Holat: {status_names.get(o.status, o.status)}"
                + (f" | Baho: {o.rating}⭐" if o.rating else "")
            )
        await update.message.reply_text("\n\n".join(lines))
    finally:
        session.close()


async def rate_driver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, order_id, stars = query.data.split(":")
    order_id, stars = int(order_id), int(stars)

    session = context.bot_data["Session"]()
    try:
        order = session.get(Order, order_id)
        if order is None or order.rating is not None or order.passenger_id != update.effective_user.id:
            await query.edit_message_text("Bu buyurtma allaqachon baholangan yoki topilmadi.")
            return
        order.rating = stars
        driver = order.driver
        if driver:
            driver.rating_sum += stars
            driver.rating_count += 1
        session.commit()
        await query.edit_message_text(f"Rahmat! Siz {stars}⭐ baho berdingiz.")
    finally:
        session.close()
