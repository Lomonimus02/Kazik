"""
Обработчики календаря активности
"""
import datetime
from typing import Optional
import logging

from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from app.config import ADMINS
from app.database.models import (
    get_activity_rewards, claim_activity_reward, get_admin_setting, 
    mark_activity, get_user_activity_streak, update_balance, 
    add_stars_to_user, add_ton_to_user, init_activity_rewards_custom, 
    get_or_create_user, get_all_orders, get_user_profile
)
from app.keyboards.main import activity_calendar_kb
from app.utils.activity_calendar import (
    format_activity_calendar, format_rewards_list, format_activity_stats,
    mark_today_activity, get_available_rewards, render_best_calendar_format, 
    get_current_date
)
from app.utils.misc import notify_admins

router = Router()

REWARDS_PER_PAGE = 5

# Настройки канала для проверки подписки
CHANNEL_ID = -1002680464877
CHANNEL_USERNAME = "@legal_stars"
CHANNEL_LINK = "https://t.me/legal_stars"

async def check_subscription(user_id: int, bot: Bot) -> bool:
    """Проверка подписки пользователя на канал"""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status not in ['left', 'kicked']
    except Exception as e:
        logging.error(f"Ошибка проверки подписки: {e}")
        return False

async def show_subscription_message(call: CallbackQuery, bot: Bot):
    """Показывает сообщение о необходимости подписки"""
    text = (
        "🔒 <b>Требуется подписка на канал</b>\n\n"
        "Для доступа к календарю активности необходимо подписаться на наш канал.\n\n"
        "Подпишитесь на канал и попробуйте снова! 👇"
    )

    # Сохраняем оригинальный callback_data для повторной проверки
    check_callback = f"check_sub_{call.data}" if call.data != "main_menu" else "check_subscription"

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="🔄 Проверить подписку", callback_data=check_callback)],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])

    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    except:
        await call.message.answer(text, parse_mode="HTML", reply_markup=markup)

class ActivityStates(StatesGroup):
    waiting_for_claim_confirmation = State()

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом"""
    return user_id in ADMINS

# Автоинициализация наград при старте
def init_activity_rewards_custom():
    """
    Инициализация только нужных призов для календаря активности (сброс каждые 30 дней)
    """
    from app.database.models import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM activity_rewards')
    rewards = [
        (3, 'balance', 15, '3 дня — 15₽ на баланс'),
        (7, 'balance', 50, '7 дней — 50₽ на баланс'),
        (15, 'stars', 13, '15 дней — 13 звёзд'),
        (21, 'stars', 21, '21 день — 21 звезда'),
        (28, 'ton', 0.1, '28 дней — 0.1 TON'),
        (30, 'ton', 0.5, '30 дней — 0.5 TON'),
    ]
    for days, rtype, amount, desc in rewards:
        cursor.execute('INSERT INTO activity_rewards (days_required, reward_type, reward_amount, description) VALUES (?, ?, ?, ?)', (days, rtype, amount, desc))
    conn.commit()
    conn.close()

# Обработчик "activity" удален, так как он дублируется с обработчиком в user.py
# В user.py уже есть правильный обработчик с проверкой подписки

@router.callback_query(F.data == "activity_calendar")
async def show_activity_calendar(callback: types.CallbackQuery):
    """Показывает красивый календарь активности"""

    # Проверка черного списка
    from app.handlers.user import check_blacklist_and_respond
    if await check_blacklist_and_respond(callback.from_user.id, callback):
        return

    # Проверка подписки (обязательная для календаря активности)
    if not await check_subscription(callback.from_user.id, callback.bot):
        await show_subscription_message(callback, callback.bot)
        return

    user_id = callback.from_user.id
    from app.database.models import get_user_profile, get_admin_setting
    profile = get_user_profile(user_id)
    if not profile:
        # Создаём пользователя, если его нет
        get_or_create_user(user_id, callback.from_user.full_name, callback.from_user.username, datetime.datetime.now().strftime("%Y-%m-%d"))

    # Получаем настройки календаря из админ панели
    calendar_description = get_admin_setting('calendar_description', '📅 <b>Календарь активности</b>\n\nОтмечайте активность каждый день и получайте награды за постоянство!')
    calendar_photo = get_admin_setting('calendar_photo', 'https://imgur.com/a/TkOPe7c.jpeg')

    now = datetime.datetime.now()
    year = now.year
    month = now.month
    from app.utils.activity_calendar import render_best_calendar_format
    calendar_text = render_best_calendar_format(user_id, year, month)

    # Добавляем описание к календарю
    full_text = f"{calendar_description}\n\n{calendar_text}"

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="activity")]]
    )

    # Удаляем предыдущее сообщение и отправляем новое с фото
    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer_photo(
        photo=calendar_photo,
        caption=full_text,
        reply_markup=kb,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "activity_rewards")
async def show_activity_rewards(callback: types.CallbackQuery):
    """Показывает награды за активность"""
    # Проверка подписки (обязательная для календаря активности)
    if not await check_subscription(callback.from_user.id, callback.bot):
        await show_subscription_message(callback, callback.bot)
        return

    user_id = callback.from_user.id
    streak = get_user_activity_streak(user_id)
    rewards = get_activity_rewards()
    from app.database.models import get_user_activity
    text = "🏆 <b>Награды за активность</b>\n\n"
    text += f"🔥 Ваша текущая серия: {streak} дней\n\n"
    text += "🎁 <b>Ваш календарь:</b>\n"
    text += f"▸ {'✅' if streak >= 3 else '◻️'} 3 день: 🪙 15₽\n"
    text += f"▸ {'✅' if streak >= 7 else '◻️'} 7 день: 💰 50₽\n"
    text += f"▸ {'✅' if streak >= 15 else '◻️'} 15 день: ⭐ 13 звёзд\n"
    text += f"▸ {'✅' if streak >= 21 else '◻️'} 21 день: ✨ 21 звезда\n"
    text += f"▸ {'✅' if streak >= 28 else '◻️'} 28 день: 💎 0.1 TON\n"
    text += f"▸ {'✅' if streak >= 30 else '◻️'} 30 день: 🔥 0.5 TON\n\n"
    keyboard = []
    for reward in rewards:
        reward_id = reward[0]
        days_required = reward[1]
        reward_type = reward[2]
        reward_amount = reward[3]
        description = reward[4]
        # Проверяем, получена ли награда
        user_acts = get_user_activity(user_id)
        already_claimed = any(
            act[3] == 'reward' and act[4] == reward_type and act[5] == reward_amount for act in user_acts
        )
        if reward_type == "balance":
            reward_text = f"{reward_amount}₽"
        elif reward_type == "stars":
            reward_text = f"{reward_amount}⭐"
        elif reward_type == "ton":
            reward_text = f"{reward_amount} TON"
        else:
            reward_text = f"{reward_amount} {reward_type}"
        if already_claimed:
            status = "✅ Получено"
        elif streak >= days_required:
            status = "✅ Доступно"
        else:
            days_left = days_required - streak
            status = f"⏳ Осталось {days_left} дней"
        text += f"• <b>{days_required} дней</b>: {reward_text}\n  {description}\n  {status}\n\n"
        # Кнопка только если не получена и доступна
        if streak >= days_required and not already_claimed:
            keyboard.append([
                types.InlineKeyboardButton(
                    text=f"🎁 Получить {reward_text}",
                    callback_data=f"claim_reward_{reward_id}"
                )
            ])
    keyboard.append([types.InlineKeyboardButton(text="⬅️ Назад", callback_data="activity")])
    try:
        if callback.message and hasattr(callback.message, 'text') and getattr(callback.message, 'text', None):
            await callback.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard))
        else:
            if callback.message and hasattr(callback.message, 'delete'):
                await callback.message.delete()
            if callback.message and hasattr(callback.message, 'answer'):
                await callback.message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception:
        if callback.message and hasattr(callback.message, 'answer'):
            await callback.message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("claim_reward_"))
async def claim_activity_reward_handler(callback: types.CallbackQuery):
    """Получение награды за активность (обновлённая механика)"""
    # Проверка подписки (обязательная для календаря активности)
    if not await check_subscription(callback.from_user.id, callback.bot):
        await show_subscription_message(callback, callback.bot)
        return

    user_id = callback.from_user.id
    reward_id = int(callback.data.replace("claim_reward_", ""))
    
    try:
        # Проверяем, не получал ли уже пользователь эту награду
        rewards = get_activity_rewards()
        reward = None
        for r in rewards:
            if r[0] == reward_id:
                reward = r
                break
        if not reward:
            await callback.answer("❌ Награда не найдена")
            return
        
        days_required = reward[1]
        reward_type = reward[2]
        reward_amount = reward[3]
        description = reward[4]
        
        # Проверяем серию активности
        streak = get_user_activity_streak(user_id)
        if streak < days_required:
            await callback.answer(f"❌ Недостаточно дней активности. Нужно: {days_required}, у вас: {streak}")
            return
        
        # Получаем профиль пользователя
        profile = get_user_profile(user_id)
        if not profile:
            await callback.answer("❌ Ошибка: профиль не найден")
            return
        
        db_user_id = profile[0]
        
        # Обрабатываем награду в зависимости от типа
        if reward_type == "balance":
            # Деньги - начисляем мгновенно
            update_balance(user_id, reward_amount)
            reward_text = f"{reward_amount}₽"
            success_message = f"✅ Награда {reward_text} начислена на ваш баланс!"
            
        elif reward_type == "stars":
            # Звёзды - создаём заявку для админов
            create_order(db_user_id, "activity_stars", reward_amount, "pending", extra_data=f"Награда за активность: {reward_amount} звезд")
            reward_text = f"{reward_amount}⭐"
            success_message = f"✅ Заявка на {reward_text} создана! Админы рассмотрят её в ближайшее время."
            
        elif reward_type == "ton":
            # TON - создаём заявку для админов
            create_order(db_user_id, "activity_ton", reward_amount, "pending", extra_data=f"Награда за активность: {reward_amount} TON")
            reward_text = f"{reward_amount} TON"
            success_message = f"✅ Заявка на {reward_text} создана! Админы рассмотрят её в ближайшее время."
            
        else:
            # Другие типы наград
            reward_text = f"{reward_amount} {reward_type}"
            success_message = f"✅ Награда {reward_text} выдана!"
        
        # Отмечаем награду как полученную
        claim_activity_reward(user_id, reward_id)
        
        # Уведомляем пользователя
        await callback.answer(success_message, show_alert=True)
        
        # Уведомляем админов о заявках на звёзды и TON
        if reward_type in ["stars", "ton"]:
            try:
                await notify_admins(
                    callback.bot,
                    f"🎁 **Новая заявка на награду за активность**\n\n"
                    f"👤 Пользователь: {callback.from_user.full_name}\n"
                    f"🆔 ID: {user_id}\n"
                    f"🏆 Награда: {reward_text}\n"
                    f"📝 Описание: {description}\n"
                    f"🔥 Серия активности: {streak} дней"
                )
            except Exception as e:
                logging.error(f"[ACTIVITY] Ошибка уведомления админов: {e}")
        
        # Обновляем отображение наград
        await show_activity_rewards(callback)
        
    except Exception as e:
        logging.error(f"[ACTIVITY] Ошибка при получении награды: {e}")
        await callback.answer("❌ Ошибка при получении награды. Попробуйте позже.", show_alert=True)

# Обработчик mark_activity удален - используется обработчик из user.py с полной логикой наград

@router.callback_query(F.data == "activity_stats")
async def activity_stats_handler(callback: types.CallbackQuery):
    """Статистика активности"""
    # Проверка подписки (обязательная для календаря активности)
    if not await check_subscription(callback.from_user.id, callback.bot):
        await show_subscription_message(callback, callback.bot)
        return

    user_id = callback.from_user.id
    # Получаем статистику
    streak = get_user_activity_streak(user_id)
    # Получаем активность за последние 30 дней
    today = datetime.datetime.now()
    activities_count = 0
    for i in range(30):
        date = today - datetime.timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        activity = get_user_activity(user_id, date_str)
        if activity:
            activities_count += 1
    text = "📊 <b>Статистика активности</b>\n\n"
    text += f"🔥 Текущая серия: {streak} дней\n"
    text += f"📅 Активность за 30 дней: {activities_count}/30 дней\n"
    text += f"📈 Процент активности: {(activities_count/30)*100:.1f}%\n\n"
    if activities_count >= 25:
        text += "🏆 Отличная активность! Продолжайте в том же духе!\n"
    elif activities_count >= 15:
        text += "👍 Хорошая активность! Старайтесь быть активнее!\n"
    else:
        text += "💪 Постарайтесь быть более активными!\n"
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="activity")]]
    )
    try:
        if callback.message and hasattr(callback.message, 'text') and getattr(callback.message, 'text', None):
            await callback.message.edit_text(text, reply_markup=kb)
        else:
            if callback.message and hasattr(callback.message, 'delete'):
                await callback.message.delete()
            if callback.message and hasattr(callback.message, 'answer'):
                await callback.message.answer(text, reply_markup=kb)
    except Exception:
        if callback.message and hasattr(callback.message, 'answer'):
            await callback.message.answer(text, reply_markup=kb)

# Админские обработчики для календаря активности
@router.callback_query(F.data == "admin_activity_stats")
async def admin_activity_stats_handler(callback: types.CallbackQuery):
    """Админская статистика активности"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    # Получаем общую статистику активности
    from app.database.models import get_all_users
    
    users = get_all_users()
    total_users = len(users)
    active_users = 0
    total_streaks = 0
    
    for user in users:
        user_id = user[1]  # tg_id
        streak = get_user_activity_streak(user_id)
        if streak > 0:
            active_users += 1
            total_streaks += streak
    
    avg_streak = total_streaks / active_users if active_users > 0 else 0
    
    text = "📊 <b>Админская статистика активности</b>\n\n"
    text += f"👥 Всего пользователей: {total_users}\n"
    text += f"🔥 Активных пользователей: {active_users}\n"
    text += f"📈 Процент активности: {(active_users/total_users)*100:.1f}%\n"
    text += f"📊 Средняя серия: {avg_streak:.1f} дней\n\n"
    
    # Топ пользователей по активности
    user_streaks = []
    for user in users:
        user_id = user[1]
        streak = get_user_activity_streak(user_id)
        if streak > 0:
            user_streaks.append((user[2], streak))  # full_name, streak
    
    user_streaks.sort(key=lambda x: x[1], reverse=True)
    
    if user_streaks:
        text += "🏆 <b>Топ активных пользователей:</b>\n"
        for i, (name, streak) in enumerate(user_streaks[:10], 1):
            text += f"{i}. {name}: {streak} дней\n"
    
    await callback.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]]
    ))

@router.callback_query(F.data == "admin_activity_users")
async def admin_activity_users_handler(callback: types.CallbackQuery):
    """Список пользователей с их активностью"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    from app.database.models import get_all_users
    
    users = get_all_users()
    
    text = "👥 <b>Активность пользователей</b>\n\n"
    
    for user in users[:20]:  # Показываем первые 20 пользователей
        user_id = user[1]  # tg_id
        full_name = user[2]
        username = user[3]
        
        streak = get_user_activity_streak(user_id)
        
        user_info = f"@{username}" if username else f"ID {user_id}"
        
        if streak > 0:
            text += f"🔥 {full_name} ({user_info}): {streak} дней\n"
        else:
            text += f"❌ {full_name} ({user_info}): неактивен\n"
    
    if len(users) > 20:
        text += f"\n... и еще {len(users) - 20} пользователей"
    
    await callback.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]]
    ))

# Логика сброса цепочки активности (streak) при пропуске хотя бы одного дня
from app.database.models import get_user_activity
import datetime

def check_and_reset_streak_on_skip(tg_id):
    today = datetime.datetime.now().date()
    streak = 0
    for i in range(1, 31):
        check_date = today - datetime.timedelta(days=i)
        acts = get_user_activity(tg_id, check_date.strftime("%Y-%m-%d"))
        if acts:
            streak += 1
        else:
            break
    # Если вчера не было активности, сбрасываем всю цепочку
    yesterday = today - datetime.timedelta(days=1)
    if not get_user_activity(tg_id, yesterday.strftime("%Y-%m-%d")):
        return True
    return False 