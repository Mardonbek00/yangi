from datetime import datetime, timedelta

import config
from keyboards import order_confirm_kb, rating_kb
from models import Driver, Order, OrderRejection
from utils import get_commission


async def try_assign_order(context, order_id: int):
    """Berilgan buyurtmani navbatdagi eng birinchi mos haydovchiga taklif qiladi."""
    session = context.bot_data["Session"]()
    try:
        order = session.get(Order, order_id)
        if order is None or order.status not in ("waiting", "offered"):
            return

        # 15 daqiqalik umumiy muddat tugaganmi
        if datetime.utcnow() - order.created_at > timedelta(seconds=config.ORDER_AUTO_CANCEL_SECONDS):
            order.status = "cancelled"
            order.driver_id = None
            session.commit()
            try:
                await context.bot.send_message(
                    order.passenger_id,
                    "😔 Kechirasiz, buyurtmangizga hozircha bo'sh haydovchi topilmadi. Buyurtma bekor qilindi.",
                )
            except Exception:
                pass
            return

        rejected_ids = {r.driver_id for r in session.query(OrderRejection).filter_by(order_id=order.id)}

        candidate = (
            session.query(Driver)
            .filter(
                Driver.status == "approved",
                Driver.is_online.is_(True),
                Driver.direction_id == order.direction_id,
                Driver.seats_taken < config.MAX_SEATS,
                Driver.balance > 0,
            )
            .order_by(Driver.queue_joined_at.asc())
            .all()
        )
        candidate = [d for d in candidate if d.user_id not in rejected_ids]

        if not candidate:
            order.status = "waiting"
            session.commit()
            return

        driver = candidate[0]
        order.status = "offered"
        order.driver_id = driver.user_id
        order.offer_expires_at = datetime.utcnow() + timedelta(seconds=config.OFFER_TIMEOUT_SECONDS)
        session.commit()

        direction_name = order.direction.name
        text = (
            f"🚕 Yangi buyurtma!\n\n"
            f"Yo'nalish: {direction_name}\n"
            f"Telefon: {order.phone}\n"
            f"Izoh: {order.comment or '—'}\n\n"
            f"{config.OFFER_TIMEOUT_SECONDS // 60} daqiqa ichida javob bering."
        )
        try:
            await context.bot.send_message(driver.user_id, text, reply_markup=order_confirm_kb(order.id))
        except Exception:
            pass

        context.job_queue.run_once(
            offer_timeout_job, config.OFFER_TIMEOUT_SECONDS,
            data={"order_id": order.id, "driver_id": driver.user_id},
            name=f"offer_timeout_{order.id}_{driver.user_id}",
        )
        context.job_queue.run_once(
            auto_cancel_job, config.ORDER_AUTO_CANCEL_SECONDS,
            data={"order_id": order.id},
            name=f"auto_cancel_{order.id}",
        )
    finally:
        session.close()


async def offer_timeout_job(context):
    data = context.job.data
    session = context.bot_data["Session"]()
    try:
        order = session.get(Order, data["order_id"])
        if order is None:
            return
        # Agar hali ham shu haydovchiga taklif qilingan holatda tursa — muddati tugagan
        if order.status == "offered" and order.driver_id == data["driver_id"]:
            session.add(OrderRejection(order_id=order.id, driver_id=data["driver_id"]))
            order.status = "waiting"
            order.driver_id = None
            session.commit()
            try:
                await context.bot.send_message(data["driver_id"], "⏱ Vaqt tugadi, buyurtma boshqa haydovchiga o'tdi.")
            except Exception:
                pass
    finally:
        session.close()
    await try_assign_order(context, data["order_id"])


async def auto_cancel_job(context):
    await try_assign_order(context, context.job.data["order_id"])


async def offer_to_driver_queue(context, driver: Driver):
    """Haydovchi liniyaga chiqqanda, o'sha yo'nalishda kutayotgan buyurtmalarni unga taklif qilish."""
    session = context.bot_data["Session"]()
    try:
        waiting = (
            session.query(Order)
            .filter(Order.direction_id == driver.direction_id, Order.status == "waiting")
            .order_by(Order.created_at.asc())
            .all()
        )
        order_ids = [o.id for o in waiting]
    finally:
        session.close()

    for oid in order_ids:
        await try_assign_order(context, oid)


async def accept_order(context, order: Order, driver: Driver, session):
    order.status = "accepted"
    driver.seats_taken += 1
    driver.balance -= get_commission(session)
    session.commit()

    direction_name = order.direction.name
    from utils import driver_card_text
    try:
        await context.bot.send_message(
            order.passenger_id,
            f"✅ Haydovchingiz topildi!\n\n{driver_card_text(driver)}\n\nYo'nalish: {direction_name}",
        )
    except Exception:
        pass

    if driver.seats_taken >= config.MAX_SEATS:
        await depart_driver(context, driver, session)


async def depart_driver(context, driver: Driver, session):
    orders = session.query(Order).filter_by(driver_id=driver.user_id, status="accepted").all()
    for order in orders:
        order.status = "completed"

    driver.is_online = False
    driver.seats_taken = 0
    driver.direction_id = None
    driver.queue_joined_at = None
    session.commit()

    for order in orders:
        try:
            await context.bot.send_message(
                order.passenger_id,
                "🚗 Safaringiz yakunlandi. Haydovchini baholang:",
                reply_markup=rating_kb(order.id),
            )
        except Exception:
            pass
