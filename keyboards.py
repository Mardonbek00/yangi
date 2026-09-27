from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup,
)

import config
from utils import is_admin


def main_menu(user_id: int, driver_status: str | None):
    rows = [["🚕 Taxi chaqirish"]]

    if driver_status == "approved":
        rows.append(["👨‍✈️ Haydovchi paneli"])
    elif driver_status == "pending":
        rows.append(["⏳ Ariza ko'rib chiqilmoqda"])
    else:
        rows.append(["🚗 Haydovchi bo'lish"])

    rows.append(["📋 Mening buyurtmalarim"])

    if is_admin(user_id):
        rows.append(["🛠 Admin panel"])

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def contact_request_kb():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Raqamni ulashish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True,
    )


def directions_kb(directions, prefix: str):
    kb = [[InlineKeyboardButton(d.name, callback_data=f"{prefix}:{d.id}")] for d in directions]
    return InlineKeyboardMarkup(kb)


def skip_comment_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("O'tkazib yuborish", callback_data="pcomment:skip")]])


def order_confirm_kb(order_id: int):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Qabul qilish", callback_data=f"daccept:{order_id}"),
        InlineKeyboardButton("❌ Rad etish", callback_data=f"dreject:{order_id}"),
    ]])


def driver_panel_kb(driver):
    if driver.is_online:
        rows = [
            [InlineKeyboardButton(f"🔴 Liniyadan chiqish ({driver.seats_taken}/{config.MAX_SEATS})", callback_data="ddepart")],
        ]
    else:
        rows = [[InlineKeyboardButton("🟢 Liniyaga chiqish", callback_data="dgoonline")]]

    rows.append([InlineKeyboardButton(f"💰 Balans: {driver.balance:,} so'm".replace(",", " "), callback_data="dbalance")])
    rows.append([InlineKeyboardButton("➕ Balansni to'ldirish", callback_data="topup:start")])
    rows.append([InlineKeyboardButton("📋 Mening safarlarim", callback_data="dtrips")])
    return InlineKeyboardMarkup(rows)


def driver_application_confirm_kb():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Yuborish", callback_data="dapp:confirm"),
        InlineKeyboardButton("❌ Bekor qilish", callback_data="dapp:cancel"),
    ]])


def admin_driver_review_kb(driver_user_id: int):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin:approve_driver:{driver_user_id}"),
        InlineKeyboardButton("❌ Rad etish", callback_data=f"admin:reject_driver:{driver_user_id}"),
    ]])


def admin_topup_review_kb(topup_id: int):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin:approve_topup:{topup_id}"),
        InlineKeyboardButton("❌ Rad etish", callback_data=f"admin:reject_topup:{topup_id}"),
    ]])


def admin_panel_kb():
    rows = [
        [InlineKeyboardButton("📊 Statistika", callback_data="admin:stats")],
        [InlineKeyboardButton("➕ Yo'nalish qo'shish", callback_data="admin:add_direction")],
        [InlineKeyboardButton("💳 Komissiya summasini o'zgartirish", callback_data="admin:set_commission")],
        [InlineKeyboardButton("🏦 Karta ma'lumotlarini o'zgartirish", callback_data="admin:set_card")],
    ]
    return InlineKeyboardMarkup(rows)


def rating_kb(order_id: int):
    row = [InlineKeyboardButton(str(n) + "⭐", callback_data=f"rate:{order_id}:{n}") for n in range(1, 6)]
    return InlineKeyboardMarkup([row])
