"""
Отладочные обработчики
"""
import datetime

from aiogram import Router, types
from aiogram.filters import Command

from app.config import ADMINS
from app.database.models import get_user_profile, get_all_orders, get_user_activity
from app.utils.activity_calendar import (
    get_user_activity_streak, get_current_month_activities,
    get_activity_rewards, format_activity_stats, mark_activity
)
from app.utils.slot_machine import get_user_slot_stats, get_last_slot_results

router = Router()

def is_admin(user_id):
    return user_id in ADMINS

@router.message(Command("debug_calendar"))
async def debug_calendar(message: types.Message):
    if not message.from_user or not hasattr(message.from_user, "id") or not is_admin(message.from_user.id):
        return
    try:
        tg_id = message.from_user.id
        raw = get_user_activity(tg_id)
        streak = get_user_activity_streak(tg_id)
        month_acts = get_current_month_activities(tg_id)
        rewards = get_activity_rewards()
        stats = format_activity_stats(tg_id)
        text = f"<b>DEBUG CALENDAR</b>\n\n"
        text += f"Raw activity (кол-во): {len(raw)}\n"
        text += f"Streak: {streak}\n"
        text += f"Month acts (кол-во): {len(month_acts)}\n"
        text += f"Rewards: {len(rewards)} шт.\n"
        text += f"\nStats:\n{stats}"
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"<b>Ошибка debug_calendar:</b> {e}", parse_mode="HTML")

@router.message(Command("debug_mark_activity"))
async def debug_mark_activity(message: types.Message):
    if not message.from_user or not hasattr(message.from_user, "id") or not is_admin(message.from_user.id):
        return
    try:
        args = message.text.split() if message.text else []
        if len(args) < 2:
            await message.answer("Использование: /debug_mark_activity YYYY-MM-DD")
            return
        date = args[1]
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except Exception:
            await message.answer("Неверный формат даты. Пример: 2024-06-28")
            return
        tg_id = message.from_user.id
        mark_activity(tg_id, date)
        await message.answer(f"Активность на {date} отмечена.")
    except Exception as e:
        await message.answer(f"<b>Ошибка debug_mark_activity:</b> {e}", parse_mode="HTML")

@router.message(Command("debug_slot"))
async def debug_slot(message: types.Message):
    if not message.from_user or not hasattr(message.from_user, "id") or not is_admin(message.from_user.id):
        return
    try:
        tg_id = message.from_user.id
        stats = get_user_slot_stats(tg_id)
        last_results = get_last_slot_results(tg_id, limit=10)
        profile = get_user_profile(tg_id)
        text = f"<b>DEBUG SLOT</b>\n\n"
        text += f"User: {profile}\n"
        text += f"Slot stats: {stats}\n"
        text += f"\nПоследние 10 попыток:\n"
        if last_results:
            for res in last_results:
                if not res:
                    continue
                try:
                    win_id, user_id, tg_id_db, full_name, combination, reward_type, reward_amount, is_win, created_at, status = res[:10]
                    reward_text = f"{reward_amount}⭐" if reward_type == "stars" else (f"{reward_amount}₽" if reward_type == "money" else "-")
                    text += f"{created_at}: {combination} | {reward_text} | {'WIN' if is_win else 'LOSE'} | {status}\n"
                except Exception as e_row:
                    text += f"Ошибка в строке: {e_row}\n"
        else:
            text += "Нет данных.\n"
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"<b>Ошибка debug_slot:</b> {e}", parse_mode="HTML")

@router.message(Command("debug_activity_orders"))
async def debug_activity_orders(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    orders = get_all_orders()
    activity_orders = [o for o in orders if o[2] in ("activity_stars", "activity_ton")]
    if not activity_orders:
        await message.answer("Нет заказов на звезды или TON.")
        return
    text = "<b>Последние activity_stars и activity_ton:</b>\n\n"
    for order in activity_orders[-10:]:
        order_id = order[0]
        user_id = order[1]
        order_type = order[2]
        amount = order[3]
        status = order[4]
        created_at = order[5]
        extra = order[7] if len(order) > 7 else ''
        user_profile = get_user_profile(user_id)
        username = user_profile[3] if user_profile else 'unknown'
        text += f"#{order_id} | {order_type} | {amount} | {status} | {created_at} | @{username}\n{extra}\n\n"
    await message.answer(text, parse_mode="HTML") 