from datetime import datetime

import config
from db import get_session
from models import Driver, Setting, User


def get_or_create_user(session, tg_user):
    user = session.get(User, tg_user.id)
    if user is None:
        user = User(id=tg_user.id, full_name=tg_user.full_name)
        session.add(user)
        session.commit()
    return user


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


def get_setting(session, key: str, default: str = "") -> str:
    row = session.get(Setting, key)
    return row.value if row else default


def set_setting(session, key: str, value: str):
    row = session.get(Setting, key)
    if row is None:
        row = Setting(key=key, value=value)
        session.add(row)
    else:
        row.value = value
    session.commit()


def get_commission(session) -> int:
    return int(get_setting(session, "commission_amount", config.DEFAULT_COMMISSION) or 0)


def get_card_info(session):
    number = get_setting(session, "card_number", "")
    holder = get_setting(session, "card_holder", "")
    return number, holder


def get_driver(session, user_id: int) -> Driver | None:
    return session.get(Driver, user_id)


def fmt_money(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " so'm"


def driver_card_text(driver: Driver) -> str:
    rating = f"{driver.avg_rating} ⭐ ({driver.rating_count} baho)" if driver.rating_count else "hali baho yo'q"
    return (
        f"👤 {driver.full_name}\n"
        f"📞 {driver.phone}\n"
        f"🚘 {driver.car_model}, {driver.car_color}, {driver.car_plate}\n"
        f"⭐ Reyting: {rating}"
    )
