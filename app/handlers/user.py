"""
Основные обработчики пользователя
"""
from app.database.models import get_user_last_activity_date,reset_user_activity
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.filters.state import StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Dispatcher, types
from app.configprem import PREMIUM_PRICES
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot
from app.database import models
import asyncio
import datetime
import json
import logging
import re
import traceback
from typing import Optional

import aiohttp
import aiosqlite
import sqlite3
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.config import ADMINS
from app.constants import CHANNEL_ID, CHANNEL_USERNAME, CHANNEL_LINK, REVIEWS_CHANNEL, REVIEW_CHANNEL_ID, PREMIUM_FIXED_PRICES, STARS_PRICES, CRYPTO_PRICES
from app.utils.misc import is_admin
from app.config_flags import ref_active, proverka
from app.database.models import (
    get_or_create_user, get_user_profile, get_referrals_count, get_all_users,
    update_balance, freeze_balance, unfreeze_balance, create_withdrawal,
    get_all_pending_withdrawals, get_withdrawal_by_id, update_withdrawal_status,
    confirm_withdrawal, get_withdrawals, get_user_profile_by_id,
    create_order, get_order_by_id, get_all_orders, update_order_status, delete_order, clear_all_orders,
    create_review, get_review_by_id, get_all_reviews, update_review_status, delete_review, clear_all_reviews,
    get_admin_setting, update_admin_setting, get_all_admin_settings,
    get_slot_configs, add_slot_config, delete_slot_config,
    get_user_slot_spins, use_slot_spin, reset_slot_spins, create_slot_win,
    get_slot_wins, update_slot_win_status, get_slot_win_by_id, delete_slot_win,
    get_activity_rewards, add_activity_reward, delete_activity_reward,
    get_user_activity, mark_activity, get_user_activity_streak, claim_activity_reward,
    get_user_referral_percent, update_user_referral_percent,
    calculate_withdrawal_commission, calculate_stars_price, get_daily_attempts_reset_time,
    should_reset_daily_attempts, get_user_share_story_status, use_share_story, reset_share_story,
    add_ton_slot_win, reset_user_activity, check_and_reset_activity_streak,
    clear_all_calendar_data, clear_all_activity_prizes, clear_all_slot_data, clear_all_slot_prizes,
    reset_all_prizes, delete_user_everywhere_full,
    add_referral_bonus_for_order_async, get_flag
)
from app.keyboards.main import (
    main_menu_inline_kb, stars_menu_inline_kb, crypto_menu_inline_kb, 
    reviews_menu_inline_kb, withdraw_confirm_kb, withdraw_requisites_kb, 
    admin_withdrawal_kb, back_to_profile_kb, admin_panel_kb,
    premium_menu_inline_kb, about_menu_inline_kb, activity_calendar_kb
)
from app.utils.activity_calendar import mark_today_activity, get_current_date
from app.utils.misc import notify_admins, process_referral_bonus
from app.handlers.admin import router as admin_router

router = Router()

class PremiumStates(StatesGroup):
    waiting_receipt_pdf = State()
    waiting_recipient = State()
    waiting_review = State()
    waiting_custom_stars = State()

class StarsStates(StatesGroup):
    waiting_receipt_pdf = State()
    waiting_recipient = State()
    waiting_review = State()

class CryptoStates(StatesGroup):
    waiting_ton = State()
    waiting_not = State()
    waiting_dogs = State()

class CryptoPayStates(StatesGroup):
    waiting_receipt_pdf = State()
    waiting_wallet = State()
    waiting_review = State()

class WithdrawStates(StatesGroup):
    waiting_amount = State()
    confirm = State()
    waiting_requisites = State()
    waiting_method = State()

class Form(StatesGroup):
    waiting_for_message_text = State()
    waiting_for_button_text = State()
    waiting_for_button_url = State()
    waiting_for_button2_text = State()
    waiting_for_button2_url = State()   
    photo_id = State()

class DBFSM(StatesGroup):
    waiting_for_page_number = State()

class AdminDBFSM(StatesGroup):
    waiting_for_page_number = State()

class AdminDB(StatesGroup):
    waiting_for_search_query = State()

class BlacklistFSM(StatesGroup):
    waiting_for_user_to_add = State()
    waiting_for_reason = State()
    waiting_for_user_to_remove = State()

class AdminFSM(StatesGroup):
    waiting_for_user_to_delete = State()

class AddReviewFSM(StatesGroup):
    waiting_for_author = State()
    waiting_for_content = State()

class AddBalanceFSM(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()

class RemoveBalanceFSM(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()
    confirm = State()

storage = MemoryStorage()




DEFAULT_MAIN_DESCRIPTION = (
    "У нас можно легально купить и подарить:\n"
    "• <b>звёзды Telegram</b> 🎁\n"
    "• <b>подписку Telegram Premium</b> 🚀\n"
    "• <b>криптовалюту TON, NOT и другие</b> 💰\n"
    "• <b>бесплатно поиграть в слот-машинку</b> и получить призы\n"
    "• <b>календарь активности</b> для наград\n\n"
    "<em>Обеспечиваем безопасность и удобство — делайте покупки легко и с уверенностью!</em> 😊"
)



async def delete_previous_message(call: types.CallbackQuery):
    try:
        if call.message:
            await call.message.delete()
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение: {e}")


# Функция проверки подписки на канал

async def check_subscription(user_id: int, bot: Bot) -> bool:
    """Проверка подписки пользователя на канал"""
    try:
        # Проверяем по CHANNEL_ID (надежнее)
        try:
            member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if member.status not in ['left', 'kicked']:
                return True
        except Exception as e:
            logging.warning(f"Ошибка проверки по ID: {e}")

        # Если по ID не сработало, проверяем по USERNAME
        try:
            member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
            return member.status not in ['left', 'kicked']
        except Exception as e:
            logging.error(f"Ошибка проверки подписки для {user_id}: {e}")
            return False
            
    except Exception as e:
        logging.error(f"Критическая ошибка в check_subscription: {e}")
        return False

async def show_subscription_message(call: CallbackQuery, bot: Bot):
    """Показывает сообщение о необходимости подписки"""
    text = (
        "🔒 <b>Требуется подписка на канал</b>\n\n"
        "Для доступа к этому разделу необходимо подписаться на наш канал.\n\n"
        "📢 <b>Почему это важно?</b>\n"
        "• Получайте актуальные новости и акции\n"
        "• Будьте в курсе новых возможностей\n"
        "• Специальные предложения только для подписчиков\n\n"
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
        
async def add_slot_attempts(user_id: int, additional_attempts: int):
    """Добавляет дополнительные попытки для слот-машины"""
    async with aiosqlite.connect('data/users.db') as db:
        # Добавляем поле для бонусных попыток
        await db.execute(
            """CREATE TABLE IF NOT EXISTS bonus_attempts (
                user_id INTEGER PRIMARY KEY,
                attempts INTEGER DEFAULT 0
            )"""
        )
        
        # Увеличиваем бонусные попытки
        await db.execute(
            """INSERT INTO bonus_attempts (user_id, attempts)
               VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET attempts = attempts + ?""",
            (user_id, additional_attempts, additional_attempts)
        )
        await db.commit()
        
@router.message(Command("add_attempts"))
async def add_attempts_command(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ Нет доступа.")
        return
    
    try:
        # Формат: /add_attempts <user_id> <количество>
        parts = message.text.split()
        if len(parts) != 3:
            raise ValueError
        
        user_id = int(parts[1])
        attempts = int(parts[2])
        
        await add_slot_attempts(user_id, attempts)
        await message.answer(f"✅ Пользователю {user_id} добавлено {attempts} попыток!")
        
        # Попробуем уведомить пользователя
        try:
            await message.bot.send_message(
                user_id,
                f"🎰 Вам добавлено {attempts} дополнительных попыток для слот-машины!"
            )
        except Exception:
            pass  # Пользователь мог заблокировать бота
            
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте: /add_attempts <user_id> <количество>")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
        logging.error(f"Error in add_attempts: {str(e)}")

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, command: CommandObject):
    # Принудительно очищаем состояние
    await state.clear()

    # Проверяем черный список
    if message.from_user:
        if await check_blacklist_and_respond(message.from_user.id, message):
            return

    # Проверяем, есть ли deep link для ответа на тикет
    if command.args and command.args.startswith("reply_"):
        # Импортируем необходимые модули для поддержки
        from app.handlers.support import admin_sessions
        from app.database.models import get_support_ticket_by_id
        import html

        # Проверяем, что пользователь - администратор
        if not message.from_user or not is_admin(message.from_user.id):
            await message.answer("❌ У вас нет доступа к этой функции.")
            return

        try:
            ticket_id = int(command.args.replace("reply_", ""))
            ticket = get_support_ticket_by_id(ticket_id)

            if not ticket:
                await message.answer("❌ Тикет не найден.")
                return

            # Сохраняем сессию админа
            admin_sessions[message.from_user.id] = {
                'ticket_id': ticket_id,
                'user_id': ticket['user_id'],
                'username': ticket['username'],
                'full_name': ticket['full_name'],
                'message': ticket['message']
            }

            # Получаем профиль пользователя для получения Telegram ID
            from app.database.models import get_user_profile_by_id
            user_profile = get_user_profile_by_id(ticket['user_id'])
            user_display = f"@{ticket['username']}" if ticket['username'] else ticket['full_name']
            user_tg_id = user_profile['tg_id'] if user_profile else "неизвестен"

            # Отправляем информацию о тикете и просим ответ
            admin_text = (
                f"✍️ <b>Ответ на тикет #{ticket_id}</b>\n\n"
                f"👤 <b>Пользователь:</b> {html.escape(user_display)}\n"
                f"🆔 <b>Telegram ID:</b> <code>{user_tg_id}</code>\n"
                f"📝 <b>Сообщение:</b>\n{html.escape(ticket['message'])}\n\n"
                f"💬 <b>Введите ваш ответ:</b>"
            )

            await message.answer(admin_text, parse_mode="HTML")
            return

        except ValueError:
            await message.answer("❌ Неверный формат ссылки.")
            return
        except Exception as e:
            await message.answer(f"❌ Ошибка: {str(e)}")
            return

    # Обычная обработка команды /start
    MAIN_PHOTO = get_admin_setting('main_photo', 'https://imgur.com/a/TkOPe7c.jpeg')
    MAIN_DESCRIPTION = get_admin_setting('main_description', DEFAULT_MAIN_DESCRIPTION)

    if not message.from_user:
        await message.answer("Ошибка: не удалось определить пользователя.")
        return

    tg_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username

    # Проверяем, есть ли уже пользователь
    user = get_user_profile(tg_id)

    if not user:
        # Обрабатываем реферальную ссылку
        referrer_id = None
        if command.args and command.args.startswith("ref_"):
            try:
                referrer_tg_id = int(command.args.replace("ref_", ""))
                # Получаем ID пригласившего по его tg_id
                referrer_profile = get_user_profile(referrer_tg_id)
                if referrer_profile and referrer_tg_id != tg_id:  # Нельзя пригласить самого себя
                    referrer_id = referrer_profile['id']
                    logging.info(f"[REFERRAL] Новый пользователь {tg_id} приглашен пользователем {referrer_tg_id}")
            except (ValueError, TypeError) as e:
                logging.warning(f"[REFERRAL] Неверный формат реферальной ссылки: {command.args}, ошибка: {e}")

        # Создаем нового пользователя с referrer_id
        reg_date = datetime.datetime.now().strftime("%Y-%m-%d")
        get_or_create_user(tg_id, full_name, username, reg_date, referrer_id)

        # Уведомляем админов
        referral_info = ""
        if referrer_id:
            referrer_profile = get_user_profile_by_id(referrer_id)
            if referrer_profile:
                referral_info = f"\n👥 Приглашен: @{referrer_profile.get('username', 'нет')} (ID: {referrer_profile['tg_id']})"

                # Уведомляем пригласившего о новом реферале
                try:
                    await message.bot.send_message(
                        referrer_profile['tg_id'],
                        f"🎉 <b>Новый реферал!</b>\n\n"
                        f"👤 Пользователь @{username or full_name} зарегистрировался по вашей ссылке!\n\n"
                        f"💡 Теперь вы можете активировать бонусные попытки в разделе 🎰 Слот-машина → 🎁 Получить бонус",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logging.warning(f"[REFERRAL] Не удалось уведомить пригласившего {referrer_profile['tg_id']}: {e}")

        await notify_admins(message.bot, f"🆕 Новый пользователь:\nИмя: {full_name}\nUsername: @{username if username else 'нет'}\nID: {tg_id}{referral_info}")

    user_caption = f"<b>@{username if username else full_name}</b>, Добро Пожаловать в Legal Stars! ✨\n\n{MAIN_DESCRIPTION}"

    # Пытаемся отправить фото, если не получается - отправляем текстом
    try:
        await message.answer_photo(
            photo=MAIN_PHOTO,
            caption=user_caption,
            reply_markup=main_menu_inline_kb(),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.warning(f"Не удалось отправить главное фото: {e}. Отправляем текстом.")
        await message.answer(
            text=user_caption,
            reply_markup=main_menu_inline_kb(),
            parse_mode="HTML"
        )

@router.callback_query(F.data == "back_to_stars_menu")
async def back_to_stars_menu(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await stars_menu(call)

@router.callback_query(F.data == "back_to_premium_menu")
async def back_to_premium_menu(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await tg_premium_menu(call)
    
@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.clear()
    await message.answer(
        "Действие отменено. Возвращаю в главное меню.",
        reply_markup=main_menu_inline_kb()
    )

@router.callback_query(F.data == "main_menu")
async def main_menu_handler(call: types.CallbackQuery):
    try:
        # Проверяем черный список
        if await check_blacklist_and_respond(call.from_user.id, call):
            return

        # Очищаем все возможные состояния
        from aiogram.filters.state import State, StatesGroup
        states = [PremiumStates, StarsStates, CryptoStates, CryptoPayStates,
                 WithdrawStates, Form, DBFSM, AdminDBFSM, AdminDB,
                 BlacklistFSM, AdminFSM, AddReviewFSM, AddBalanceFSM,
                 RemoveBalanceFSM]

        for state_group in states:
            try:
                await call.bot.current_state(user=call.from_user.id).reset_state()
            except:
                pass

        MAIN_PHOTO = get_admin_setting('main_photo', 'https://imgur.com/a/TkOPe7c.jpeg')
        MAIN_DESCRIPTION = get_admin_setting('main_description', DEFAULT_MAIN_DESCRIPTION)

        await delete_previous_message(call)

        if proverka and not await check_subscription(call.from_user.id, call.bot):
            await show_subscription_message(call, call.bot)
            return

        try:
            await call.message.answer_photo(
                photo=MAIN_PHOTO,
                caption=MAIN_DESCRIPTION,
                reply_markup=main_menu_inline_kb()
            )
        except Exception as photo_error:
            logging.warning(f"Не удалось отправить главное фото: {photo_error}. Отправляем текстом.")
            await call.message.answer(
                text=MAIN_DESCRIPTION,
                reply_markup=main_menu_inline_kb(),
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"Error in main_menu_handler: {e}")
        await call.answer("⚠️ Произошла ошибка. Попробуйте еще раз.")

async def main_menu_handler_no_delete(call: types.CallbackQuery):
    """Обработчик главного меню БЕЗ удаления предыдущего сообщения (для рассылки)"""
    try:
        # Проверяем черный список
        if await check_blacklist_and_respond(call.from_user.id, call):
            return

        MAIN_PHOTO = get_admin_setting('main_photo', 'https://imgur.com/a/TkOPe7c.jpeg')
        MAIN_DESCRIPTION = get_admin_setting('main_description', DEFAULT_MAIN_DESCRIPTION)

        # НЕ удаляем предыдущее сообщение (рассылку)

        if proverka and not await check_subscription(call.from_user.id, call.bot):
            await show_subscription_message(call, call.bot)
            return

        try:
            await call.message.answer_photo(
                photo=MAIN_PHOTO,
                caption=MAIN_DESCRIPTION,
                reply_markup=main_menu_inline_kb()
            )
        except Exception as photo_error:
            logging.warning(f"Не удалось отправить главное фото: {photo_error}. Отправляем текстом.")
            await call.message.answer(
                text=MAIN_DESCRIPTION,
                reply_markup=main_menu_inline_kb(),
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"Error in main_menu_handler_no_delete: {e}")
        await call.answer("⚠️ Произошла ошибка. Попробуйте еще раз.")
        
@router.errors()
async def errors_handler(error_event: types.ErrorEvent):
    try:
        update = error_event.update
        exception = error_event.exception

        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer("⚠️ Произошла ошибка. Попробуйте еще раз.")
        elif hasattr(update, 'message') and update.message:
            await update.message.answer("⚠️ Произошла ошибка. Попробуйте еще раз.", reply_markup=main_menu_inline_kb())
    except:
        pass

    logging.error(f"Update: {error_event.update}\nException: {error_event.exception}")
    return True

@router.callback_query(F.data == "check_subscription")
async def check_subscription_handler(callback: types.CallbackQuery):
    is_subscribed = await check_subscription(callback.from_user.id, callback.bot)
    
    if is_subscribed:
        await callback.answer("✅ Подписка подтверждена!")
        try:
            await callback.message.delete()
        except Exception:
            pass
            
        # Параметры для главного меню из админ панели
        MAIN_PHOTO = get_admin_setting('main_photo', 'https://imgur.com/a/TkOPe7c.jpeg')
        MAIN_TITLE = "Добро Пожаловать в Legal Stars! ✨"
        MAIN_DESCRIPTION = (
            "У нас можно легально купить и подарить:\n"
            "• <b>звёзды Telegram</b> 🎁\n"
            "• <b>подписку Telegram Premium</b> 🚀\n"
            "• <b>криптовалюту TON, NOT и другие</b> 💰\n"
            "• <b>бесплатно поиграть в слот-машинку</b> и получить призы\n"
            "• <b>календарь активности</b> для наград\n\n"
            "<em>Обеспечиваем безопасность и удобство — делайте покупки легко и с уверенностью!</em> 😊"
        )

        try:
            await callback.message.answer_photo(
                photo=MAIN_PHOTO,
                caption=f"{MAIN_TITLE}\n\n{MAIN_DESCRIPTION}",
                reply_markup=main_menu_inline_kb()
            )
        except Exception as photo_error:
            logging.warning(f"Не удалось отправить главное фото: {photo_error}. Отправляем текстом.")
            await callback.message.answer(
                text=f"{MAIN_TITLE}\n\n{MAIN_DESCRIPTION}",
                reply_markup=main_menu_inline_kb(),
                parse_mode="HTML"
            )
    else:
        await callback.answer("❌ Подписка не найдена. Подпишитесь на канал и попробуйте снова.")

@router.callback_query(F.data.startswith("check_sub_"))
async def check_subscription_for_section(callback: types.CallbackQuery):
    """Проверка подписки для конкретного раздела"""
    is_subscribed = await check_subscription(callback.from_user.id, callback.bot)

    if is_subscribed:
        # Извлекаем оригинальный callback_data
        original_callback = callback.data.replace("check_sub_", "")

        # Перенаправляем на соответствующий раздел
        if original_callback == "tg_premium":
            await tg_premium_menu(callback)
        elif original_callback == "stars":
            await stars_menu(callback)
        elif original_callback == "crypto":
            await crypto_menu(callback)
        else:
            # Если неизвестный раздел, возвращаем в главное меню
            await main_menu_handler(callback)
    else:
        await callback.answer("❌ Подписка не найдена. Подпишитесь на канал и попробуйте снова.")

@router.callback_query(F.data == "activity")
async def activity_menu_from_main(call: types.CallbackQuery, bot: Bot):
    await delete_previous_message(call)
    if not await check_subscription(call.from_user.id, bot):
        await show_subscription_message(call, bot)
        return

    try:
        user_id = call.from_user.id
        current_date = datetime.datetime.now().date()
        
        # Получаем серию из БД
        from app.database.models import get_user_activity_streak
        streak = get_user_activity_streak(user_id)
        
        text = (
            "<b>📅 Календарь активности</b>\n\n"
            "Календарь активности — это когда пользователь заходит в бота и отмечает свою активность за текущий день.\n"
            "Если пользователь заходит подряд несколько дней (например, 7, 14 или 20 дней), он получает награду или бонус.\n"
            "Если пользователь пропускает хотя бы один день, его \"цепочка\" активности сбрасывается — счетчик возвращается к нулю.\n"
            "Например: пользователь зашел 20 дней подряд, а на 21-й день не зашел — его прогресс сбрасывается до нуля.\n\n"
            f"<b>🔥 Ваша текущая серия:</b> {streak} дней\n"
            f"📌 <b>Сегодня:</b> {current_date.strftime('%d.%m.%Y')}"
        )

        await call.message.answer(
            text,
            reply_markup=activity_calendar_kb(),
            parse_mode="HTML"
        )

    except Exception as e:
        logging.error(f"Ошибка в activity_menu: {str(e)}")
        await call.answer("⚠️ Произошла ошибка", show_alert=True)

@router.callback_query(F.data == "mark_activity")
async def mark_user_activity(call: types.CallbackQuery):
    # Проверка подписки (обязательная для календаря активности)
    if not await check_subscription(call.from_user.id, call.bot):
        await show_subscription_message(call, call.bot)
        return

    try:
        user_id = call.from_user.id
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        # Проверяем, была ли уже отмечена активность сегодня (используем БД)
        from app.database.models import get_user_activity, mark_activity, get_user_activity_streak
        existing_activity = get_user_activity(user_id, today_str)

        if existing_activity:
            # Активность уже отмечена сегодня
            await call.answer("Вы уже подтвердили свою активность, приходите завтра! 😊🚀", show_alert=True)
            return

        # Отмечаем активность в БД
        mark_activity(user_id, today_str, "daily")

        # Получаем обновленную серию из БД
        streak = get_user_activity_streak(user_id)

        # Проверяем награды
        rewards = {
            3: "15₽ на баланс",
            7: "50₽ на баланс",
            15: "13⭐",
            21: "21⭐",
            28: "0.1 TON",
            30: "0.5 TON"
        }

        reward_text = ""
        if streak in rewards:
            reward = rewards[streak]
            if streak in [3, 7]:  # Награды в рублях
                update_balance(user_id, int(reward.split('₽')[0]))
            elif streak in [15, 21]:  # Награды в звездах - создаем заявку
                stars_amount = int(reward.split('⭐')[0])
                # Создаем заказ для админов
                from app.database.models import create_order, get_user_profile
                profile = get_user_profile(user_id)
                if profile:
                    db_user_id = profile['id']
                    create_order(db_user_id, "activity_stars", stars_amount, "pending",
                               extra_data=f"Награда за активность: {stars_amount} звезд (серия {streak} дней)")

                    # Уведомляем админов о заявке
                    try:
                        from app.utils.misc import notify_admins
                        await notify_admins(
                            call.bot,
                            f"⭐ НОВАЯ ЗАЯВКА НА ЗВЕЗДЫ ЗА АКТИВНОСТЬ ⭐\n\n"
                            f"👤 Пользователь: {call.from_user.full_name}\n"
                            f"🆔 ID: {user_id}\n"
                            f"🏆 Награда: {stars_amount}⭐\n"
                            f"🔥 Серия активности: {streak} дней\n"
                            f"📅 Дата: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        )
                    except Exception as e:
                        import logging
                        logging.error(f"Ошибка уведомления админов о звездах: {e}")
            elif streak in [28, 30]:  # Награды в TON - создаем заявку
                ton_amount = float(reward.split(' TON')[0])
                # Создаем заказ для админов
                from app.database.models import create_order, get_user_profile
                profile = get_user_profile(user_id)
                if profile:
                    db_user_id = profile['id']
                    create_order(db_user_id, "activity_ton", ton_amount, "pending",
                               extra_data=f"Награда за активность: {ton_amount} TON (серия {streak} дней)")

                    # Уведомляем админов о заявке
                    try:
                        from app.utils.misc import notify_admins
                        await notify_admins(
                            call.bot,
                            f"💎 НОВАЯ ЗАЯВКА НА TON ЗА АКТИВНОСТЬ 💎\n\n"
                            f"👤 Пользователь: {call.from_user.full_name}\n"
                            f"🆔 ID: {user_id}\n"
                            f"🏆 Награда: {ton_amount} TON\n"
                            f"🔥 Серия активности: {streak} дней\n"
                            f"📅 Дата: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        )
                    except Exception as e:
                        import logging
                        logging.error(f"Ошибка уведомления админов о TON: {e}")
            # Формируем текст награды в зависимости от типа
            if streak in [3, 7]:  # Деньги - начислены мгновенно
                reward_text = f"\n\n🎉 Поздравляем! Награда {reward} начислена на ваш баланс!"
            elif streak in [15, 21, 28, 30]:  # Звезды и TON - создана заявка
                reward_text = f"\n\n🎉 Поздравляем! Заявка на {reward} создана! Админы рассмотрят её в ближайшее время."
            else:
                reward_text = f"\n\n🎉 Поздравляем! Вы получили награду: {reward}"

        await call.answer(f"✅ Активность отмечена! Текущая серия: {streak} дней{reward_text}")

        # Обновляем сообщение
        current_date = datetime.datetime.now().strftime('%d.%m.%Y')
        await call.message.edit_text(
            f"<b>📅 Календарь активности</b>\n\n"
            f"Календарь активности — это когда пользователь заходит в бота и отмечает свою активность за текущий день.\n"
            f"Если пользователь заходит подряд несколько дней (например, 7, 14 или 20 дней), он получает награду или бонус.\n"
            f"Если пользователь пропускает хотя бы один день, его \"цепочка\" активности сбрасывается — счетчик возвращается к нулю.\n"
            f"Например: пользователь зашел 20 дней подряд, а на 21-й день не зашел — его прогресс сбрасывается до нуля.\n\n"
            f"<b>🔥 Ваша текущая серия:</b> {streak} дней\n"
            f"📌 <b>Сегодня:</b> {current_date}{reward_text}",
            reply_markup=activity_calendar_kb(),
            parse_mode="HTML"
        )

    except Exception as e:
        logging.error(f"Ошибка при отметке активности: {e}")
        await call.answer("⚠️ Произошла ошибка", show_alert=True)

# Универсальный возврат в главное меню для message (например, после загрузки чека)
async def send_main_menu(message):
    from app.database.models import get_admin_setting
    main_photo = get_admin_setting('main_photo', 'https://imgur.com/a/TkOPe7c.jpeg')
    main_title = get_admin_setting('main_title', 'Legal Stars!')
    main_description = get_admin_setting('main_description', 'У нас вы можете легально купить и подарить:\n• <b>звёзды Telegram</b> друзьям 🎁\n• <b>оформить подписку</b> себе или друзьям Telegram Premium 🚀\n• <b>приобрести криптовалюту</b>, такую как TON, NOT и другие 💰\n• <b>а также поиграть бесплатно слот-машинку</b> и получить призы\n• <b>и календарь активности</b> для получения наград\n\n<em>Обеспечиваем безопасность и удобство — делайте покупки легко и с уверенностью!</em> 😊')
    user = getattr(message, 'from_user', None)
    username = f"@{user.username}" if user and getattr(user, 'username', None) else (user.full_name if user else "Пользователь")
    caption = f"<b>{username}, Добро Пожаловать в Legal Stars! ✨</b>\n\n{main_description}"
    if message is not None and hasattr(message, "answer_photo"):
        try:
            await message.answer_photo(
                photo=main_photo,
                caption=caption,
                reply_markup=main_menu_inline_kb(),
                parse_mode="HTML"
            )
        except Exception as photo_error:
            logging.warning(f"Не удалось отправить главное фото: {photo_error}. Отправляем текстом.")
            await message.answer(
                text=caption,
                reply_markup=main_menu_inline_kb(),
                parse_mode="HTML"
            )


@router.callback_query(F.data == "tg_premium")
async def tg_premium_menu(call: types.CallbackQuery):
    await delete_previous_message(call)

    # Проверяем черный список
    if await check_blacklist_and_respond(call.from_user.id, call):
        return

    # Проверка подписки (только если включена в настройках)
    from app.config_flags import proverka
    if proverka and not await check_subscription(call.from_user.id, call.bot):
        await show_subscription_message(call, call.bot)
        return
        
    premium_photo = get_admin_setting('premium_photo', 'https://imgur.com/a/VJU8JNk.jpeg')
    premium_description = get_admin_setting('premium_description', '💎 Telegram Premium — это официальная подписка от Telegram, дающая дополнительные возможности. Выберите желаемый срок подписки:')
    kb = premium_menu_inline_kb()
    await call.message.answer_photo(
        photo=premium_photo,
        caption=premium_description,
        reply_markup=kb
    )
    


# Обработчик кнопки "Назад" на экране "Загрузить чек" (возврат к выбору тарифа)
@router.callback_query(F.data.in_(["premium_3m", "premium_6m", "premium_12m"]), StateFilter(PremiumStates.waiting_receipt_pdf))
async def back_from_upload_receipt_to_tariff(callback: types.CallbackQuery, state: FSMContext):
    logging.info(f"Back from upload receipt to tariff: callback_data={callback.data}")
    await state.clear()
    await callback.message.delete()

    # Возвращаемся к меню выбора тарифа Premium
    await tg_premium_menu(callback)

# Обработчик кнопки "Назад" на экране загрузки чека (старый путь Premium)
@router.callback_query(lambda c: c.data.startswith('pay_sbp_'), StateFilter(PremiumStates.waiting_receipt_pdf))
async def back_from_premium_receipt_pdf(callback: types.CallbackQuery, state: FSMContext):
    logging.info(f"Back from premium receipt PDF: callback_data={callback.data}")

    await state.clear()
    await callback.message.delete()

    parts = callback.data.split('_')
    tariff = '_'.join(parts[2:-1])
    price = parts[-1]

    logging.info(f"Back from premium receipt PDF: tariff={tariff}, price={price}")

    # Определяем период для отображения
    period = {
        '3m': '3 месяца',
        '6m': '6 месяцев',
        '12m': '12 месяцев',
        'premium_3m': '3 месяца',
        'premium_6m': '6 месяцев',
        'premium_12m': '12 месяцев'
    }.get(tariff, '?')

    text = (
        f"<b>Оплатите {price}₽ за Telegram Premium ({period})</b>\n"
        f"По номеру: <code>+79912148689</code>\n"
        f"Банк: <i>Альфа-Банк</i>\n\n"
        f"После оплаты загрузите чек"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧾 Загрузить чек", callback_data=f"upload_receipt_{tariff}_{price}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"premium_{tariff.replace('premium_', '')}")]
    ])

    # Восстанавливаем состояние для возможности повторной загрузки чека
    await state.update_data(tariff=tariff, price=float(price))
    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

# --- Оплата через СБП ---
@router.callback_query(F.data.startswith("pay_sbp_"))
async def pay_sbp_menu(call: types.CallbackQuery, state: FSMContext):
    try:
        await call.message.delete()
    except:
        pass
    
    # More robust parsing of callback data
    parts = call.data.split('_')
    if len(parts) < 4:
        await call.answer("❌ Неверный формат данных")
        return
        
    tariff = '_'.join(parts[2:-1])  # Handle cases where tariff might contain underscores
    price = parts[-1]
    
    try:
        price = float(price)
    except ValueError:
        await call.answer("❌ Неверная цена")
        return
    
    period = {
        '3m': '3 месяца',
        '6m': '6 месяцев',
        '12m': '12 месяцев',
        'premium_3m': '3 месяца',
        'premium_6m': '6 месяцев', 
        'premium_12m': '12 месяцев'
    }.get(tariff, '?')
    
    text = (
        f"<b>Оплатите {price}₽ за Telegram Premium ({period})</b>\n"
        f"По номеру: <code>+79912148689</code>\n"
        f"Банк: <i>Альфа-Банк</i>\n\n"
        f"После оплаты загрузите чек"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧾 Загрузить чек", callback_data=f"upload_receipt_{tariff}_{price}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"premium_{tariff.replace('premium_', '')}")]
    ])
    
    await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.update_data(tariff=tariff, price=price)

@router.callback_query(F.data.startswith("upload_receipt_"))
async def upload_receipt_start(call: types.CallbackQuery, state: FSMContext):
    try:
        if getattr(call, 'message', None) and hasattr(call.message, "delete"):
            await call.message.delete()
    except Exception:
        pass

    # Правильно разбираем callback_data: upload_receipt_tariff_price
    key = call.data.replace('upload_receipt_', '') if call.data else ''
    parts = key.split('_')
    if len(parts) >= 2:
        tariff = '_'.join(parts[:-1])  # Все части кроме последней
        price = parts[-1]  # Последняя часть - цена
    else:
        tariff = key
        price = ''

    await state.update_data(tariff=tariff, price=price)

    text = (
        "💬 Отправьте файл с чеком (PDF формат - обязательно) для проверки администрацией:\n\n"
        "❗ Требования к чеку:\n"
        "- Формат: PDF\n"
        "- Макс. размер: 5MB\n"
        "- Чек должен быть читаемым"
    )

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"pay_sbp_{tariff}_{price}")],
        ]
    )

    if getattr(call, 'message', None) and hasattr(call.message, "answer"):
        await call.message.answer(text, reply_markup=kb)

    await state.set_state(PremiumStates.waiting_receipt_pdf)

@router.message(PremiumStates.waiting_receipt_pdf, F.document)
async def premium_handle_pdf_receipt(message: types.Message, state: FSMContext):
    # Получаем данные из состояния
    data = await state.get_data()
    tariff = data.get('tariff', '')
    price = data.get('price', '')

    # Проверяем, что файл - PDF
    file_name = message.document.file_name or ""
    if not file_name.lower().endswith('.pdf'):
        await message.answer(
            "❌ Неверный формат чека. Пожалуйста, отправляйте только файлы в формате PDF.\n"
            "Попробуйте ещё раз, но уже с форматом PDF.\n"
            "Если у вас возникнут вопросы, не стесняйтесь связаться со мной."
        )
        return

    # Проверка размера файла (максимум 5MB)
    if message.document.file_size > 5 * 1024 * 1024:
        error_text = (
            "❌ Файл слишком большой. Максимальный размер - 5MB.\n\n"
            "Пожалуйста, сожмите файл или отправьте другой чек.\n\n"
            "Если у вас не получается, обратитесь в поддержку:"
        )
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="📩 Связаться с поддержкой", url="https://t.me/Black_Prince01")],
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"pay_sbp_{tariff}_{price}")],
            ]
        )
        await message.answer(error_text, reply_markup=kb)
        return

    # Сохраняем file_id чека
    await state.update_data(
        receipt_file_id=message.document.file_id,
        receipt_file_name=file_name or "receipt.pdf"
    )

    text = (
        "✅ Чек получен!\n\n"
        "Теперь укажите получателя Premium:\n"
        "- Отправьте @username пользователя\n"
        "- Или напишите 'мне', если оформляете для себя"
    )

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"upload_receipt_{tariff}_{price}")],
        ]
    )
    
    await message.answer(text, reply_markup=kb)
    await state.set_state(PremiumStates.waiting_recipient)

@router.message(PremiumStates.waiting_receipt_pdf, ~F.document)
async def premium_handle_wrong_receipt_format(message: Message, state: FSMContext):
    if message.text and message.text.strip() == '/cancel':
        return  # обрабатывается отдельным хендлером

    data = await state.get_data()
    key = data.get('tariff', '')
    price = data.get('price', '')

    # Определяем, через какой путь пришел пользователь
    # Если есть premium_price и period, значит пришел через новый путь
    # Если нет, но есть tariff и price, значит старый путь
    premium_price = data.get('premium_price')
    period = data.get('period')
    is_new_path = premium_price is not None and period is not None

    # Логирование для отладки
    logging.info(f"Premium wrong format: data={data}, is_new_path={is_new_path}")

    error_text = (
        "❌ Неверный формат чека. Пожалуйста, отправляйте только файлы в формате PDF.\n"
        "Попробуйте ещё раз, но уже с форматом PDF.\n"
        "Если у вас возникнут вопросы, не стесняйтесь связаться со мной."
    )

    # Используем правильный callback_data в зависимости от пути
    if is_new_path:
        back_callback = "premium_pay_sbp"
    else:
        # Для старого пути используем pay_sbp_ формат
        back_callback = f"pay_sbp_{key}_{price}"

    logging.info(f"Premium wrong format: back_callback={back_callback}")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📩 Связаться с поддержкой", url="https://t.me/Black_Prince01")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback)],
    ])

    await message.answer(error_text, reply_markup=kb)
    # НЕ очищаем состояние, чтобы сообщение повторялось при каждой ошибке

# Дублирующий обработчик удален - используется более функциональный обработчик ниже

@router.message(CryptoPayStates.waiting_receipt_pdf, ~F.document)
async def crypto_handle_wrong_receipt_format(message: Message, state: FSMContext):
    if message.text and message.text.strip() == '/cancel':
        return  # обрабатывается отдельным хендлером

    error_text = (
        "❌ Неверный формат чека. Пожалуйста, отправляйте только файлы в формате PDF.\n"
        "Попробуйте ещё раз, но уже с форматом PDF.\n"
        "Если у вас возникнут вопросы, не стесняйтесь связаться со мной."
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📩 Связаться с поддержкой", url="https://t.me/Black_Prince01")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto")],
    ])

    await message.answer(error_text, reply_markup=kb)
    # НЕ очищаем состояние, чтобы сообщение повторялось при каждой ошибке

# Обработчик кнопки "Назад" в состоянии ожидания PDF для Crypto
@router.callback_query(CryptoPayStates.waiting_receipt_pdf, F.data == "crypto_confirm")
async def crypto_back_from_pdf(callback: types.CallbackQuery, state: FSMContext):
    # Получаем данные из состояния перед очисткой
    data = await state.get_data()
    coin = data.get('coin', '?')
    amount = data.get('amount', '?')
    total = data.get('total', 0.0)

    # Очищаем состояние
    await state.clear()

    try:
        await callback.message.delete()
    except Exception:
        pass

    # Если данных нет, возвращаем в меню криптовалют
    if not data or coin == '?' or amount == '?' or total == 0.0:
        await crypto_menu(callback)
        return

    text = (
        f"<b>Оплатите {total:.2f}₽ за {amount} {coin}</b>\n"
        f"По номеру: <code>+79912148689</code> (кликабельно для копирования)\n"
        f"Банк: <i>Альфа-Банк</i>\n\n"
        f"После оплаты нажмите кнопку ниже, чтобы загрузить чек"
    )

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🧾 Загрузить чек", callback_data="crypto_upload_receipt")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto")],
        ]
    )

    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    # Сохраняем данные обратно в состояние для возможности повторного использования
    await state.update_data(coin=coin, amount=amount, total=total)

 # Изменяем обработчик выбора тарифа Premium
@router.callback_query(F.data.in_(["premium_3m", "premium_6m", "premium_12m"]))
async def premium_choose_pay_method(call: types.CallbackQuery, state: FSMContext):
    is_subscribed = await check_subscription(call.from_user.id, call.bot)
    if not is_subscribed:
        await show_subscription_message(call, call.bot)
        return
    
    # Используем фиксированные цены из словаря
    if call.data == "premium_3m":
        period = "3 месяца"
        price = PREMIUM_FIXED_PRICES['3m']
        tariff_key = "3m"
    elif call.data == "premium_6m":
        period = "6 месяцев"
        price = PREMIUM_FIXED_PRICES['6m']
        tariff_key = "6m"
    elif call.data == "premium_12m":
        period = "12 месяцев"
        price = PREMIUM_FIXED_PRICES['12m']
        tariff_key = "12m"
    else:
        return
        
    await state.update_data(
        premium_price=price,
        period=period,
        tariff=tariff_key
    )
    
    text = f"Вы выбрали <b>{period}</b> Telegram Premium.\n💰 Сумма к оплате: <b>{price}₽</b>\n\nВыберите способ оплаты:"
    keyboard = [
        [InlineKeyboardButton(text="📱 СБП", callback_data=f"premium_pay_sbp_{tariff_key}"),
         InlineKeyboardButton(text="💰 Криптовалюта", callback_data=f"premium_pay_crypto_{tariff_key}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="tg_premium")]
    ]
    
    try:
        await call.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    except Exception:
        await call.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

# Обработчик оплаты СБП (единственный, без дублей)
@router.callback_query(F.data.startswith("premium_pay_sbp_"))
async def premium_pay_sbp_menu(call: types.CallbackQuery, state: FSMContext):
    try:
        await call.message.delete()
    except:
        pass
    
    # Получаем данные из состояния
    data = await state.get_data()
    tariff_key = data.get('tariff')
    price = data.get('premium_price')
    period = data.get('period')
    
    if not tariff_key or not price:
        await call.answer("❌ Ошибка данных. Попробуйте снова.")
        return
    
    text = (
        f"<b>Оплатите {price}₽ за Telegram Premium ({period})</b>\n"
        f"По номеру: <code>+79912148689</code>\n"
        f"Банк: <i>Альфа-Банк</i>\n\n"
        f"После оплаты загрузите чек"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧾 Загрузить чек", callback_data=f"premium_upload_receipt")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"premium_{tariff_key}")]
    ])
    
    await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.update_data(tariff=tariff_key, price=price)

# Обработчик загрузки чека
@router.callback_query(F.data == "premium_upload_receipt")
async def premium_upload_receipt_start(call: types.CallbackQuery, state: FSMContext):
    # Проверяем, что данные о тарифе и цене сохранены
    data = await state.get_data()
    if "tariff" not in data or "price" not in data:
        await call.answer("❌ Ошибка: данные не найдены. Начните заново.")
        await tg_premium_menu(call)  # Возвращаем в меню Premium
        return
    try:
        await call.message.delete()
    except:
        pass
    
    text = (
        "💬 Отправьте файл с чеком (PDF формат - обязательно) для проверки администрацией:\n\n"
        "❗ Требования к чеку:\n"
        "- Формат: PDF\n"
        "- Макс. размер: 5MB\n"
        "- Чек должен быть читаемым"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="premium_pay_sbp")]
    ])
    
    await call.message.answer(text, reply_markup=kb)
    await state.set_state(PremiumStates.waiting_receipt_pdf)

# Обработчик кнопки "Назад" для нового Premium обработчика
@router.callback_query(F.data == "premium_pay_sbp", StateFilter(PremiumStates.waiting_receipt_pdf))
async def back_from_premium_upload_receipt(callback: types.CallbackQuery, state: FSMContext):
    # Получаем данные из состояния перед очисткой
    data = await state.get_data()
    tariff_key = data.get('tariff')
    price = data.get('premium_price')
    period = data.get('period')

    await state.clear()
    await callback.message.delete()

    # Воссоздаем предыдущий экран оплаты СБП
    if tariff_key and price and period:
        text = (
            f"<b>Оплатите {price}₽ за Telegram Premium ({period})</b>\n"
            f"По номеру: <code>+79912148689</code>\n"
            f"Банк: <i>Альфа-Банк</i>\n\n"
            f"После оплаты загрузите чек"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧾 Загрузить чек", callback_data=f"premium_upload_receipt")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"premium_{tariff_key}")]
        ])

        # Восстанавливаем состояние для возможности повторной загрузки чека
        await state.update_data(tariff=tariff_key, price=price, premium_price=price, period=period)
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        # Если данных нет, возвращаемся в главное меню Premium
        await tg_premium_menu(callback)

@router.message(PremiumStates.waiting_recipient)
async def process_recipient(message: types.Message, state: FSMContext):
    # Получаем данные из состояния
    data = await state.get_data()
    recipient_raw = (message.text or '').strip().lower()

    if recipient_raw == "мне":
        recipient = f"@{message.from_user.username or message.from_user.id}"
    else:
        # Убираем @ если он есть в начале, затем добавляем обратно
        username = recipient_raw.lstrip('@')
        recipient = f"@{username}"

    # Получаем database ID пользователя
    user_profile = get_user_profile(message.from_user.id)
    if not user_profile:
        await message.answer("❌ Ошибка: пользователь не найден в базе данных.")
        await state.clear()
        return

    # Создаем заказ в базе данных
    order_id = create_order(
        user_id=user_profile['id'],  # Используем database ID
        order_type="premium",
        amount=data.get('premium_price', 0),
        status="pending",
        file_id=data.get('receipt_file_id'),
        extra_data={
            'period': data.get('period', ''),
            'recipient': recipient
        }
    )

    # Формируем текст сообщения
    order_info = (
        f"🌟 <b>НОВЫЙ ЗАКАЗ TELEGRAM PREMIUM</b> 🌟\n\n"
        f"👤 <b>Клиент:</b> @{message.from_user.username or message.from_user.id}\n"
        f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
        f"📦 <b>Получатель:</b> {recipient}\n"
        f"⏳ <b>Срок подписки:</b> {data.get('period', '?')}\n"
        f"💵 <b>Стоимость:</b> <b>{data.get('premium_price', 0)}₽</b>\n"
        f"🕒 <b>Дата/время:</b> {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        f"📌 <b>Номер заказа:</b> <code>{order_id}</code>\n\n"
        f"#заказ #{order_id}"
    )

    # Создаем клавиатуру для админов
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"order_pay_{order_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"order_reject_{order_id}"),
        ],
        [
            InlineKeyboardButton(text="🗑 Удалить заказ", callback_data=f"order_delete_{order_id}")
        ]
    ])

    # Отправляем информацию админам
    try:
        for admin_id in ADMINS:
            try:
                if data.get('receipt_file_id'):
                    # Отправляем сообщение с прикрепленным чеком
                    admin_msg = await message.bot.send_document(
                        chat_id=admin_id,
                        document=data.get('receipt_file_id'),
                        caption=order_info,
                        reply_markup=admin_kb,
                        parse_mode="HTML"
                    )
                else:
                    # Если чека нет, отправляем просто текст
                    admin_msg = await message.bot.send_message(
                        chat_id=admin_id,
                        text=order_info,
                        reply_markup=admin_kb,
                        parse_mode="HTML"
                    )
                
                # Обновляем ID сообщения в базе данных
                update_order_status(order_id, admin_msg_id=admin_msg.message_id)
                
            except Exception as admin_error:
                logging.error(f"Ошибка отправки заказа админу {admin_id}: {admin_error}")
                continue

    except Exception as e:
        logging.error(f"Критическая ошибка при обработке заказа: {e}")
        await message.answer(
            "⚠️ Произошла ошибка при отправке заказа. Пожалуйста, попробуйте позже.",
            reply_markup=main_menu_inline_kb()
        )
        return

    # Отправляем подтверждение пользователю
    await message.answer(
        "✅ Ваш заказ на Telegram Premium успешно отправлен на проверку!\n\n"
        "Администратор проверит ваш чек и активирует подписку в ближайшее время.",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🛍️ Оставить отзыв", callback_data="leave_review")],
            [types.InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")],
        ])
    )
    
    # Очищаем состояние
    await state.clear()

@router.callback_query(F.data == "leave_review")
async def leave_review_entry(call: types.CallbackQuery, state: FSMContext):
    msg = getattr(call, 'message', None)
    if msg:
        try:
            await msg.delete()
        except Exception:
            pass
    await call.message.answer(
        "✍️ Напишите ваш отзыв или отправьте фото. Отзыв будет опубликован после модерации.\n\n"
        "📝 Вы можете:\n"
        "• Отправить только текст\n"
        "• Отправить только фото (в <b>сжатом виде</b>)\n"
        "• Отправить фото с подписью",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
            ]
        ),
        parse_mode="HTML"
    )
    await state.set_state(PremiumStates.waiting_review)

def format_author(user):
    if user.username:
        return f"@{user.username}"
    return f"{user.id}"

@router.message(PremiumStates.waiting_review)
async def process_review(message: types.Message, state: FSMContext):
    # Проверяем, что есть хотя бы текст или фото
    if not message.text and not message.photo:
        await message.answer(
            "Пожалуйста, отправьте текст отзыва или фото для отзыва.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]]
            )
        )
        return

    user = message.from_user
    # Текст может быть пустым, если есть только фото
    review_text = message.text or (message.caption if message.caption else '')
    review_id = create_review(
        user_id=user.id,
        content=review_text,
        file_id=message.photo[-1].file_id if message.photo else None,
        status="pending"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"review_publish_{review_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"review_reject_{review_id}"),
        ],
        [
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"review_delete_{review_id}")
        ]
    ])
    author = format_author(user)
    text = (
        f"📝 Новый отзыв от {author}\n"
        f"ID: {user.id}\n\n"
        f"{review_text}"
    )
    admin_msgs = []
    if message.photo and len(message.photo) > 0:
        # Для фото с текстом или без текста
        if review_text.strip():
            text_plain = f"📝 Новый отзыв от {author}\nID: {user.id}\n\n{review_text}"
        else:
            text_plain = f"📝 Новый отзыв (только фото) от {author}\nID: {user.id}"

        photo_file_id = message.photo[-1].file_id
        for admin_id in ADMINS:
            try:
                admin_msg = await message.bot.send_photo(admin_id, photo_file_id, caption=text_plain, reply_markup=markup)
                admin_msgs.append((admin_id, admin_msg.message_id))
            except Exception as e:
                logging.warning(f"Не удалось отправить фото админу {admin_id}: {e}")
                # Если не удалось отправить фото, отправляем текстом
                try:
                    admin_msg = await message.bot.send_message(admin_id, text_plain, reply_markup=markup, parse_mode="HTML")
                    admin_msgs.append((admin_id, admin_msg.message_id))
                except Exception as e2:
                    logging.error(f"Не удалось отправить текст админу {admin_id}: {e2}")
    else:
        # Только текст без фото
        admin_msgs = await send_to_admins(message.bot, text, reply_markup=markup, parse_mode="HTML")
    if admin_msgs:
        update_review_status(review_id, admin_msg_id=admin_msgs[0][1])
    await message.answer(
        "Спасибо! Ваш отзыв будет проверен и скоро опубликован❤️",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")],
            ]
        )
    )
    await state.clear()
    
@router.callback_query(F.data.startswith("review_reject_"))
async def review_reject(callback: types.CallbackQuery):
    import datetime
    try:
        review_id = int(callback.data.split("_")[2])
        from app.database.models import get_review_by_id, update_review_status
        review = get_review_by_id(review_id)
        update_review_status(review_id, status="rejected")
        reject_time = datetime.datetime.now().strftime('%H:%M %d.%m.%Y')
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            f"❌ Отзыв отклонён\n<b>Время отклонения:</b> {reject_time}",
            parse_mode="HTML"
        )
        await callback.answer("❌ Отзыв отклонён")
    except Exception as e:
        try:
            await callback.answer(f"❌ Ошибка: {str(e)}")
        except Exception:
            pass

@router.callback_query(F.data.startswith("review_delete_"))
async def review_delete(callback: types.CallbackQuery):
    try:
        review_id = int(callback.data.split("_")[2])
        # Удаляем отзыв из базы
        from app.database.models import delete_review
        delete_review(review_id)
        
        await callback.answer("🗑 Отзыв удалён")
        await callback.message.delete()
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}")

# Дальнейшие шаги TG Premium будут добавлены ниже

@router.callback_query(F.data == "about")
async def about_menu(call: types.CallbackQuery, bot: Bot):
    await delete_previous_message(call)
    """Меню 'О нас' с проверкой подписки"""
    # Проверяем подписку
    if not await check_subscription(call.from_user.id, bot):
        await show_subscription_message(call, bot)
        return

    try:
        # Контент для раздела "О нас"
        about_photo = "https://imgur.com/a/nG1DXzq.jpeg"
        about_text = (
    "🌟 Legal Stars: Ваш Путь к Звёздам! 🌟\n\n"
    "Добро пожаловать в Legal Stars! Здесь вы можете легко и безопасно приобрести:\n"
    "• 🎁 Звёзды Telegram друзьям\n"
    "• 🚀 Подписку Telegram Premium себе или друзьям\n"
    "• 💰 Криптовалюту — TONCOIN, NOTCOIN и другие\n\n"
    "По самым выгодным ценам!\n"
    "Добавим волшебство в вашу жизнь без лишних забот, не беспокоясь о возвратах.\n\n"
    "✨ Почему выбирают нас?\n\n"
    "💸 Доступные цены: самые низкие цены на рынке для тех, кто хочет космического сияния.\n"
    "🛡 Легальность: все транзакции защищены — ваше спокойствие гарантировано.\n"
    "⚙️ Простота: всего несколько кликов — и звёзды ваши!\n\n"
    "🚀 Присоединяйтесь к нам и откройте мир возможностей с Legal Stars!"
)
        
        # Пытаемся отправить фото с текстом
        try:
            await call.message.answer_photo(
                photo=about_photo,
                caption=about_text,
                reply_markup=about_menu_inline_kb(),
                parse_mode="HTML"
            )
        except Exception as photo_error:
            logging.warning(f"Ошибка отправки фото: {photo_error}")
            await call.message.answer(
                about_text,
                reply_markup=about_menu_inline_kb(),
                parse_mode="HTML"
            )
        
        await call.answer()

    except Exception as e:
        logging.error(f"Ошибка в about_menu: {e}")
        await call.answer("❌ Ошибка загрузки информации", show_alert=True)

@router.callback_query(F.data == "check_about_sub")
async def check_about_subscription(call: CallbackQuery, bot: Bot):
    """Проверка подписки при нажатии кнопки"""
    if await check_subscription(call.from_user.id, bot):
        await about_menu(call, bot)  # Показываем раздел "О нас"
    else:
        await call.answer("❌ Вы ещё не подписались на канал", show_alert=True)

@router.callback_query(F.data == "reviews")
async def reviews_menu(call: types.CallbackQuery, bot: Bot):
    await delete_previous_message(call)
    """Меню отзывов с проверкой подписки"""

    # Проверяем черный список
    if await check_blacklist_and_respond(call.from_user.id, call):
        return

    if not await check_subscription(call.from_user.id, bot):
        await show_subscription_message(call, bot)  # Передаем оба аргумента
        return

    try:
        reviews_photo = "https://imgur.com/a/5cDMyX0.jpeg"
        reviews_text = (
    "🌟 Отзывы наших клиентов 🌟\n\n"
    "Мы ценим ваше мнение и стремимся сделать наш сервис лучше с каждым днем! "
    "Здесь вы можете ознакомиться с отзывами наших клиентов, которые уже приобрели звёзды через LegalStars. "
    "Ваши впечатления важны для нас!\n\n"
    "💬 Оставьте свой отзыв!\n\n"
    "Ваш опыт может помочь другим пользователям сделать правильный выбор. "
    "Поделитесь своими впечатлениями о покупке звёзд, качестве обслуживания "
    "и общем опыте взаимодействия с нашим ботом."
)
        
        try:
            await call.message.answer_photo(
                photo=reviews_photo,
                caption=reviews_text,
                reply_markup=reviews_menu_inline_kb(),
                parse_mode="HTML"
            )
        except Exception as e:
            await call.message.answer(
                reviews_text,
                reply_markup=reviews_menu_inline_kb(),
                parse_mode="HTML"
            )
        
        await call.answer()

    except Exception as e:
        logging.error(f"Ошибка в reviews_menu: {e}")
        await call.answer("❌ Ошибка загрузки", show_alert=True)

@router.callback_query(F.data == "check_reviews_sub")
async def check_reviews_subscription(call: CallbackQuery, bot: Bot):
    """Проверка подписки после нажатия кнопки"""
    if await check_subscription(call.from_user.id, bot):
        await reviews_menu(call, bot)
    else:
        await call.answer("❌ Вы ещё не подписались", show_alert=True)

@router.message(Command("admin"))
async def adminmenu(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.answer("Нет доступа.")
        return
    users_count = len(get_all_users())
    from app.config_flags import proverka, ref_active
    from app.keyboards.main import admin_panel_kb
    text = (
        f"<b>Панель администратора:</b>\n"
        f"👤 Пользователей: <b>{users_count}</b>\n"
        f"🔒 Проверка на подписку: {'✅' if proverka else '⛔️'}\n"
        f"Рефералы: {'✅' if ref_active else '⛔️'}"
    )
    kb = admin_panel_kb()
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

def get_admin_panel_text_and_kb_actual():
    from app.config_flags import proverka, ref_active
    from app.database.models import get_all_users
    from app.keyboards.main import admin_panel_kb
    users_count = len(get_all_users())
    text = (
        f"<b>Панель администратора:</b>\n"
        f"👤 Пользователей: <b>{users_count}</b>\n"
        f"🔒 Проверка на подписку: {'✅' if proverka else '⛔️'}\n"
        f"Рефералы: {'✅' if ref_active else '⛔️'}"
    )
    kb = admin_panel_kb()
    return text, kb

@router.callback_query(F.data == "toggle_check")
async def toggle_check(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("Нет доступа.")
        return
    
    # Импортируем и изменяем глобальный флаг
    from app.config_flags import proverka
    global proverka
    proverka = not proverka
    
    # Обновляем значение в модуле config_flags
    import app.config_flags
    app.config_flags.proverka = proverka
    
    # Обновляем сообщение с админ-панелью
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    text, kb = get_admin_panel_text_and_kb_actual()
    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    
    await callback.answer(f"Проверка подписки {'включена ✅' if proverka else 'выключена ⛔️'}")

@router.callback_query(F.data == "toggle_ref")
async def toggle_ref(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("Нет доступа.")
        return
    global ref_active
    from app.config_flags import ref_active
    ref_active = not ref_active
    import app.config_flags
    app.config_flags.ref_active = ref_active
    try:
        await callback.message.delete()
    except Exception:
        pass
    text, kb = get_admin_panel_text_and_kb_actual()
    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "state_proverka_on")
async def cb_proverka_on(callback: types.CallbackQuery):
    from app.database.models import get_all_users
    from app.config_flags import proverka, ref_active
    user_count = len(get_all_users())
    check_emoji = "✅" if proverka else "⛔️"
    ref_emoji = "✅" if ref_active else "⛔️"
    text = (
        f"Панель администратора:\n"
        f"👤 Пользователей: {user_count}\n"
        f"🔒 Проверка на подписку: {check_emoji}\n"
        f"Рефералы: {ref_emoji}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"ПРОВЕРКА: {check_emoji} {'ВЫКЛ' if not proverka else 'ВКЛ'}", callback_data="state_proverka_on" if not proverka else "state_proverka_off")],
        [InlineKeyboardButton(text=f"Рефералы: {ref_emoji} {'ВКЛ' if ref_active else 'ВЫКЛ'}", callback_data="state_ref_on" if not ref_active else "state_ref_off")],
        [InlineKeyboardButton(text="💬РАССЫЛКА", callback_data="rassilka")],
        [InlineKeyboardButton(text="📂 База данных", callback_data="admin_db")],
        [InlineKeyboardButton(text="🚫 Чёрный список", callback_data="blacklist_menu")],
        [InlineKeyboardButton(text="🗑 Удалить пользователя", callback_data="delete_user")],
        [InlineKeyboardButton(text="➕ Добавить отзыв", callback_data="add_review")],
        [InlineKeyboardButton(text="📋 Все заявки", callback_data="admin_orders")],
        [InlineKeyboardButton(text="🧹 Очистить заявки", callback_data="admin_clear_orders")],
        [InlineKeyboardButton(text="🗑 Скрыть", callback_data="hide_admin_panel")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data == 'rassilka')
async def textrassilka(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "✍️ Введите текст сообщения.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='⬅️ Назад', callback_data='admin_panel')]
        ])
    )
    await state.set_state(Form.waiting_for_message_text)
    
@router.message(Form.waiting_for_message_text)
async def namebutton(message: types.Message, state: FSMContext):
    await state.update_data(waiting_for_message_text=message.text)
    await message.answer(
        '✅ Текст принят\n✍️ Введите название первой кнопки',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='⬅️ Назад', callback_data='admin_panel')]
        ])
    )
    await state.set_state(Form.waiting_for_button_text)

@router.message(Form.waiting_for_button_text)
async def buttonname(message: types.Message, state: FSMContext):
    await state.update_data(button_text=message.text)
    await message.answer(
        "✅ Название первой кнопки принято.\n\n✍️ Теперь введите <b>ссылку или внутреннюю команду</b> "
        "для первой кнопки.\n\n"
        "Если это ссылка — укажите её полностью, например: https://example.com\n"
        "Если хотите, чтобы кнопка открывала раздел в боте, используйте одну из этих команд:\n\n"
        "<code>buystars</code> — Открывает раздел покупки звёзд\n"
        "<code>generalmenu</code> — Вернуться в главное меню\n"
        "<code>reviewsmenu</code> — Перейти к разделу с отзывами\n"
        "<code>buyprem</code> — Открывает раздел покупки Premium\n"
        "<code>cryptoshop</code> — Открывает раздел покупки криптовалюты\n"
        "<code>slot_machine</code> — Открывает раздел слот-машины\n"
        "<code>activity</code> — Открывает календарь активности\n"
        "<code>profile</code> — Открывает профиль пользователя\n"
        "<code>support</code> — Открывает раздел поддержки\n"
        "<code>reviews</code> — Открывает раздел отзывов\n"
        "<code>legal_channel</code> — Ссылка на канал Legal Stars",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='⬅️ Назад', callback_data='admin_panel')]
        ])
    )
    await state.set_state(Form.waiting_for_button_url)

@router.message(Form.waiting_for_button_url)
async def waiturl(message: types.Message, state: FSMContext):
    await state.update_data(message_buttonlink=message.text)
    await message.answer(
        '✅ Ссылка для первой кнопки получена\n✍️ Введите название второй кнопки ("Паблик" или другое)',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='⬅️ Назад', callback_data='admin_panel')]
        ])
    )
    await state.set_state(Form.waiting_for_button2_text)

@router.message(Form.waiting_for_button2_text)
async def button2name(message: types.Message, state: FSMContext):
    await state.update_data(button2_text=message.text)
    await message.answer(
        "✅ Название второй кнопки принято.\n\n✍️ Теперь введите <b>ссылку или внутреннюю команду</b> "
        "для второй кнопки.\n\n"
        "Если это ссылка — укажите её полностью, например: https://example.com\n"
        "Если хотите, чтобы кнопка открывала раздел в боте, используйте одну из этих команд:\n\n"
        "<code>buystars</code> — Открывает раздел покупки звёзд\n"
        "<code>generalmenu</code> — Вернуться в главное меню\n"
        "<code>reviewsmenu</code> — Перейти к разделу с отзывами\n"
        "<code>buyprem</code> — Открывает раздел покупки Premium\n"
        "<code>cryptoshop</code> — Открывает раздел покупки криптовалюты\n"
        "<code>slot_machine</code> — Открывает раздел слот-машины\n"
        "<code>activity</code> — Открывает календарь активности\n"
        "<code>profile</code> — Открывает профиль пользователя\n"
        "<code>support</code> — Открывает раздел поддержки\n"
        "<code>reviews</code> — Открывает раздел отзывов\n"
        "<code>legal_channel</code> — Ссылка на канал Legal Stars",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='⬅️ Назад', callback_data='admin_panel')]
        ])
    )
    await state.set_state(Form.waiting_for_button2_url)

@router.message(Form.waiting_for_button2_url)
async def waiturl2(message: types.Message, state: FSMContext):
    await state.update_data(message_button2link=message.text)
    await message.answer(
        '✅ Ссылка для второй кнопки получена\n✍️ Теперь отправьте фото, которое будет прикреплено '
        '(если фото не будет, введите "безфото")',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='⬅️ Назад', callback_data='admin_panel')]
        ])
    )
    await state.set_state(Form.photo_id)

async def send_message_to_user(bot, tg_id, message_text, markup):
    try:
        await bot.send_message(tg_id, message_text, reply_markup=markup)
    except Exception as e:
        print(f"[ERR] Не удалось отправить сообщение {tg_id}: {e}")

async def send_photo_to_user(bot, tg_id, photo_id, caption, markup):
    try:
        await bot.send_photo(tg_id, photo=photo_id, caption=caption, reply_markup=markup)
    except Exception as e:
        print(f"[ERR] Не удалось отправить фото {tg_id}: {e}")

async def broadcast_message(bot, message_text, markup):
    from app.database.models import get_all_users
    users = get_all_users()
    user_ids = [row[1] for row in users]  # tg_id
    batch_size = 30
    for i in range(0, len(user_ids), batch_size):
        batch = user_ids[i:i + batch_size]
        await asyncio.gather(*(send_message_to_user(bot, tg_id, message_text, markup) for tg_id in batch))
        await asyncio.sleep(1)

async def broadcast_photo(bot, photo_id, caption, markup):
    from app.database.models import get_all_users
    users = get_all_users()
    user_ids = [row[1] for row in users]  # tg_id
    batch_size = 30
    for i in range(0, len(user_ids), batch_size):
        batch = user_ids[i:i + batch_size]
        await asyncio.gather(*(send_photo_to_user(bot, tg_id, photo_id, caption, markup) for tg_id in batch))
        await asyncio.sleep(1)

def estimate_broadcast_time(user_count: int, batch_size: int = 30, delay: float = 1.0) -> str:
    total_batches = (user_count + batch_size - 1) // batch_size
    estimated_seconds = total_batches * delay + total_batches * 1.5  # 1.5 сек на отправку
    minutes = int(estimated_seconds // 60)
    seconds = int(estimated_seconds % 60)
    return f"{minutes} мин {seconds} сек" if minutes > 0 else f"{seconds} сек"

@router.message(Form.photo_id)
async def buttonlink(message: types.Message, state: FSMContext):
    data = await state.get_data()
    message_text = data['waiting_for_message_text']
    button_name = data['button_text']
    button_url = data['message_buttonlink']
    button2_name = data.get('button2_text', '')  # Получаем название второй кнопки
    button2_url = data.get('message_button2link', '')  # Получаем ссылку второй кнопки
    
    # Создаем список для кнопок
    buttons = []
    
    # Обработка первой кнопки
    if button_name and button_url and button_name.strip() and button_url.strip():
        if button_url.lower() in ['buystars', 'generalmenu', 'reviewsmenu', 'buyprem', 'cryptoshop', 'slot_machine', 'activity', 'profile', 'support', 'reviews']:
            buttons.append(InlineKeyboardButton(text=button_name, callback_data=button_url.lower()))
        elif button_url.lower() == 'legal_channel':
            buttons.append(InlineKeyboardButton(text=button_name, url='https://t.me/legal_stars'))
        elif button_url.startswith(('http://', 'https://')):
            buttons.append(InlineKeyboardButton(text=button_name, url=button_url))
        else:
            # Проверяем, что это валидный URL, а не просто число
            if '.' in button_url and not button_url.isdigit():
                fixed_url = f'https://{button_url}' if not button_url.startswith(('http://', 'https://')) else button_url
                buttons.append(InlineKeyboardButton(text=button_name, url=fixed_url))
            else:
                # Если это число или невалидный URL, используем как callback_data
                callback_data = button_url.lower()[:64]  # Ограничиваем длину callback_data
                buttons.append(InlineKeyboardButton(text=button_name, callback_data=callback_data))

    # Обработка второй кнопки (если есть)
    if button2_name and button2_url and button2_name.strip() and button2_url.strip():
        if button2_url.lower() in ['buystars', 'generalmenu', 'reviewsmenu', 'buyprem', 'cryptoshop', 'slot_machine', 'activity', 'profile', 'support', 'reviews']:
            buttons.append(InlineKeyboardButton(text=button2_name, callback_data=button2_url.lower()))
        elif button2_url.lower() == 'legal_channel':
            buttons.append(InlineKeyboardButton(text=button2_name, url='https://t.me/legal_stars'))
        elif button2_url.startswith(('http://', 'https://')):
            buttons.append(InlineKeyboardButton(text=button2_name, url=button2_url))
        else:
            # Проверяем, что это валидный URL, а не просто число
            if '.' in button2_url and not button2_url.isdigit():
                fixed_url = f'https://{button2_url}' if not button2_url.startswith(('http://', 'https://')) else button2_url
                buttons.append(InlineKeyboardButton(text=button2_name, url=fixed_url))
            else:
                # Если это число или невалидный URL, используем как callback_data
                callback_data = button2_url.lower()[:64]  # Ограничиваем длину callback_data
                buttons.append(InlineKeyboardButton(text=button2_name, callback_data=callback_data))
    
    # Создаем клавиатуру с кнопками (в одну строку)
    markup = InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None

    from app.database.models import get_all_users
    user_count = len(get_all_users())

    # Локальная функция для расчета времени рассылки
    def estimate_broadcast_time_local(user_count: int, batch_size: int = 30, delay: float = 1.0) -> str:
        total_batches = (user_count + batch_size - 1) // batch_size
        estimated_seconds = total_batches * delay + total_batches * 1.5  # 1.5 сек на отправку
        minutes = int(estimated_seconds // 60)
        seconds = int(estimated_seconds % 60)
        return f"{minutes} мин {seconds} сек" if minutes > 0 else f"{seconds} сек"

    estimated_time = estimate_broadcast_time_local(user_count)
    
    if message.text and message.text.lower() == 'безфото':
        await message.answer(
            f"🚀 Начинаю рассылку без фото...\n👥 Пользователей: {user_count}\n⏱ Примерное время: {estimated_time}")
        asyncio.create_task(broadcast_message(message.bot, message_text, markup))
        await message.answer("✅ Рассылка запущена.")
        await state.clear()
        return
        
    if message.content_type == 'photo':
        photo_id = message.photo[-1].file_id
        await message.answer_photo(
            photo=photo_id, 
            caption=message_text, 
            reply_markup=markup
        )
        await message.answer(
            f"🚀 Начинаю рассылку с фото...\n👥 Пользователей: {user_count}\n⏱ Примерное время: {estimated_time}")
        asyncio.create_task(broadcast_photo(message.bot, photo_id, message_text, markup))
        await message.answer("✅ Рассылка с фото запущена.")
        await state.clear()
        return
        
    # Если нет фото и не указано 'безфото', отправляем просто текст
    await message.answer(
        f"🚀 Начинаю рассылку без фото...\n👥 Пользователей: {user_count}\n⏱ Примерное время: {estimated_time}")
    asyncio.create_task(broadcast_message(message.bot, message_text, markup))
    await message.answer("✅ Рассылка запущена.")
    await state.clear()

# Обработчики для внутренних команд (используются в рассылке)
@router.callback_query(F.data == 'buystars')
async def handle_buystars(callback: types.CallbackQuery):
    """Обработчик кнопки buystars - НЕ удаляет сообщение рассылки"""
    await callback.answer()
    await stars_menu_no_delete(callback)

@router.callback_query(F.data == 'generalmenu')
async def handle_generalmenu(callback: types.CallbackQuery):
    """Обработчик кнопки generalmenu в рассылке - возврат в главное меню БЕЗ удаления сообщения"""
    await callback.answer()
    # НЕ удаляем сообщение рассылки, просто отправляем главное меню
    await main_menu_handler_no_delete(callback)

@router.callback_query(F.data == 'reviewsmenu')
async def handle_reviewsmenu(callback: types.CallbackQuery):
    """Обработчик кнопки reviewsmenu - НЕ удаляет сообщение рассылки"""
    await callback.answer()
    await reviews_menu_no_delete(callback, callback.bot)

@router.callback_query(F.data == 'buyprem')
async def handle_buyprem(callback: types.CallbackQuery):
    """Обработчик кнопки buyprem - НЕ удаляет сообщение рассылки"""
    await callback.answer()
    await tg_premium_menu_no_delete(callback)

@router.callback_query(F.data == 'cryptoshop')
async def handle_cryptoshop(callback: types.CallbackQuery):
    """Обработчик кнопки cryptoshop - НЕ удаляет сообщение рассылки"""
    await callback.answer()
    await crypto_menu_no_delete(callback)

@router.callback_query(F.data == 'slot_machine')
async def handle_slot_machine(callback: types.CallbackQuery):
    """Обработчик кнопки slot_machine - НЕ удаляет сообщение рассылки"""
    await callback.answer()
    from app.handlers.slot_machine import slot_machine_menu_no_delete
    await slot_machine_menu_no_delete(callback)

@router.callback_query(F.data == 'activity')
async def handle_activity(callback: types.CallbackQuery):
    """Обработчик кнопки activity - НЕ удаляет сообщение рассылки"""
    await callback.answer()
    await activity_menu_from_main_no_delete(callback, callback.bot)

@router.callback_query(F.data == 'profile')
async def handle_profile(callback: types.CallbackQuery):
    """Обработчик кнопки profile - НЕ удаляет сообщение рассылки"""
    await callback.answer()
    # Создаем пустой FSMContext для совместимости
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.memory import MemoryStorage
    storage = MemoryStorage()
    state = FSMContext(storage=storage, key=f"user:{callback.from_user.id}")
    await profile_menu_no_delete(callback, callback.bot, state)

@router.callback_query(F.data == 'support')
async def handle_support(callback: types.CallbackQuery):
    """Обработчик кнопки support - НЕ удаляет сообщение рассылки"""
    await callback.answer()
    from app.handlers.support import support_menu_no_delete
    await support_menu_no_delete(callback, callback.bot)



@router.callback_query(F.data == "admin_db")
async def admin_db_start(callback: types.CallbackQuery, state: FSMContext):
    await render_db_page(callback.message, 0)

async def render_db_page(message, page: int):
    from app.database.models import get_all_users
    users = get_all_users()
    per_page = 5
    total_users = len(users)
    total_pages = (total_users + per_page - 1) // per_page
    if page < 0 or page >= total_pages:
        await message.answer(f"❗ Всего страниц: {total_pages}. Укажите число от 1 до {total_pages}.")
        return
    start = page * per_page
    end = start + per_page
    users_page = users[start:end]
    text = f"<b>📦 База данных (стр. {page + 1} из {total_pages})</b>\n\n"
    for user in users_page:
        tg_id = user[1]
        username = user[3] or '—'
        balance = user[5] if len(user) > 5 else 0
        regdate = user[4] or '—'
        ref_id = user[7] if len(user) > 7 else None
        # Считаем сколько пригласил
        from app.database.models import get_referrals_count
        ref_count = get_referrals_count(tg_id)
        text += (f"👤 ID: <code>{tg_id}</code>\n"
                 f"📛 Username: @{username}\n"
                 f"💰 Баланс: {balance:.2f}₽\n"
                 f"📅 Регистрация: {regdate}\n"
                 f"🔗 Пригласил: <code>{ref_id or '—'}</code>\n"
                 f"👥 Приглашено: {ref_count}\n\n")
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_db_page:{page - 1}"))
    if (page + 1) < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Вперёд", callback_data=f"admin_db_page:{page + 1}"))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        nav_buttons,
        [InlineKeyboardButton(text="🔢 Перейти к странице", callback_data="admin_db_goto")],
        [InlineKeyboardButton(text="Выход", callback_data="admin_panel")],
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="admin_db_search")]
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@router.callback_query(F.data.startswith("admin_db_page:"))
async def handle_db_page(callback: types.CallbackQuery):
    page = int(callback.data.split(":")[1])
    await callback.message.delete()
    await render_db_page(callback.message, page)

@router.callback_query(F.data == "admin_db_goto")
async def ask_page_number(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите номер страницы, к которой хотите перейти:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️Назад', callback_data='admin_db')]]))
    await state.set_state(AdminDBFSM.waiting_for_page_number)

@router.message(AdminDBFSM.waiting_for_page_number)
async def go_to_specific_page(message: types.Message, state: FSMContext):
    try:
        page_number = int(message.text.strip())
        if page_number < 1:
            raise ValueError
        await state.clear()
        await render_db_page(message, page_number - 1)
    except ValueError:
        await message.answer("❗ Введите корректный номер страницы (целое число ≥ 1)")

@router.callback_query(F.data == "admin_db_search")
async def admin_db_search(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminDB.waiting_for_search_query)
    await callback.message.answer("🔍 Введите ID или username (можно с @ и в любом регистре):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️Назад', callback_data='admin_db')]]))

@router.message(AdminDB.waiting_for_search_query)
async def admin_db_search_query(message: types.Message, state: FSMContext):
    query = message.text.strip()

    # Нормализуем поисковый запрос
    if query.startswith('@'):
        query = query[1:]  # Убираем @ если есть

    from app.database.models import get_all_users, get_user_profile, get_referrals_count
    users = get_all_users()
    found_user = None
    for user in users:
        tg_id = str(user[1])
        username = user[3] or ''
        if query.isdigit() and tg_id == query:
            found_user = user
            break
        elif query.lower() in username.lower():
            found_user = user
            break
    if not found_user:
        await message.answer("❗ Пользователь не найден.")
        await state.clear()
        return
    # Получаем подробную информацию о пользователе
    tg_id = found_user[1]
    username = found_user[3] or '—'
    balance = found_user[5] if len(found_user) > 5 else 0
    regdate = found_user[4] or 'None'
    ref_id = found_user[7] if len(found_user) > 7 else None
    # Получаем username пригласившего
    inviter = '—'
    if ref_id:
        inviter_profile = None
        for u in users:
            if u[0] == ref_id:
                inviter_profile = u
                break
        if inviter_profile:
            if isinstance(inviter_profile, dict):
                inviter = f"@{inviter_profile['username']}" if inviter_profile['username'] else f"ID: {inviter_profile['tg_id']}"
            else:
                inviter = f"@{inviter_profile[3]}" if inviter_profile[3] else f"ID: {inviter_profile[1]}"
    # Получаем рефералов
    from app.database.models import get_all_users
    referrals = []
    for u in users:
        if u[7] == found_user[0]:
            ref_username = u[3] or f"ID: {u[1]}"
            ref_balance = u[5] if len(u) > 5 else 0
            referrals.append((ref_username, ref_balance))
    # Формируем текст
    text = (
        f"<b>🔍 Найден пользователь</b>\n\n"
        f"<b>ID:</b> {tg_id}\n"
        f"<b>Username:</b> @{username}\n"
        f"<b>Баланс:</b> {balance:.2f}₽\n"
        f"<b>Регистрация:</b> {regdate}\n"
        f"<b>Пригласил:</b> {inviter}\n"
        f"<b>👥 Рефералы:</b>\n"
    )
    if referrals:
        for ref_username, ref_balance in referrals:
            text += f"  └ @{ref_username}: {ref_balance:.2f}₽\n"
    else:
        text += "  —"
    # Кнопки управления
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить баланс", callback_data="add_balance"), InlineKeyboardButton(text="Убрать баланс", callback_data="remove_balance")],
        [InlineKeyboardButton(text="⬅️Назад", callback_data="admin_db")]
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)
    await state.clear()

async def get_blacklist():
    rows = []
    async with aiosqlite.connect('data/blacklist.db') as db:
        await db.execute('CREATE TABLE IF NOT EXISTS blacklist (tg_id INTEGER PRIMARY KEY, reason TEXT, date_added TEXT)')
        await db.commit()
        async with db.execute('SELECT tg_id, reason, date_added FROM blacklist') as cursor:
            rows = await cursor.fetchall()
    return rows

async def add_to_blacklist(tg_id, reason):
    async with aiosqlite.connect('data/blacklist.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS blacklist (tg_id INTEGER PRIMARY KEY, reason TEXT, date_added TEXT)''')
        await db.execute('INSERT OR REPLACE INTO blacklist (tg_id, reason, date_added) VALUES (?, ?, ?)', (tg_id, reason, datetime.datetime.now().strftime('%Y-%m-%d')))
        await db.commit()

async def remove_from_blacklist(tg_id):
    async with aiosqlite.connect('data/blacklist.db') as db:
        await db.execute('DELETE FROM blacklist WHERE tg_id = ?', (tg_id,))
        await db.commit()

async def is_blacklisted(tg_id):
    """Проверяет, находится ли пользователь в черном списке"""
    async with aiosqlite.connect('data/blacklist.db') as db:
        await db.execute('CREATE TABLE IF NOT EXISTS blacklist (tg_id INTEGER PRIMARY KEY, reason TEXT, date_added TEXT)')
        await db.commit()
        async with db.execute('SELECT reason FROM blacklist WHERE tg_id = ?', (tg_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

async def check_blacklist_and_respond(user_id, message_or_callback):
    """Универсальная функция проверки черного списка с отправкой сообщения"""
    blacklist_reason = await is_blacklisted(user_id)
    if blacklist_reason:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📞 Связаться", url="https://t.me/legal_stars")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
        ])

        blacklist_message = (
            f"🚫 <b>Доступ ограничен</b>\n\n"
            f"Вы находитесь в черном списке.\n"
            f"📝 Причина: {blacklist_reason}\n\n"
            f"Для решения вопроса обратитесь в поддержку."
        )

        if hasattr(message_or_callback, 'message'):  # CallbackQuery
            try:
                await message_or_callback.message.delete()
            except Exception:
                pass
            await message_or_callback.message.answer(blacklist_message, reply_markup=kb, parse_mode="HTML")
        else:  # Message
            await message_or_callback.answer(blacklist_message, reply_markup=kb, parse_mode="HTML")

        return True
    return False

@router.callback_query(F.data == "blacklist_menu")
async def show_blacklist(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    rows = await get_blacklist()
    text = "<b>📛 Чёрный список пользователей</b>\n"
    if not rows:
        text += "\nПока что пусто ✅"
    else:
        async with aiosqlite.connect("data/users.db") as users_db:
            for tg_id, reason, date in rows:
                cursor = await users_db.execute("SELECT username FROM users WHERE tg_id = ?", (tg_id,))
                user = await cursor.fetchone()
                username = f"@{user[0]}" if user and user[0] else "(без имени)"
                text += f"\n• {username} (<code>{tg_id}</code>) — {reason} ({date})"
    # Создаем кнопки для каждого пользователя в ЧС
    buttons = []
    if rows:
        for tg_id, reason, date in rows:
            async with aiosqlite.connect("data/users.db") as users_db:
                cursor = await users_db.execute("SELECT username FROM users WHERE tg_id = ?", (tg_id,))
                user = await cursor.fetchone()
                username = f"@{user[0]}" if user and user[0] else f"ID:{tg_id}"
                buttons.append([InlineKeyboardButton(text=f"🚫 Снять ЧС: {username}", callback_data=f"blacklist_unban_{tg_id}")])

    buttons.append([InlineKeyboardButton(text="➕ Добавить в ЧС", callback_data="blacklist_add")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=markup)

@router.callback_query(F.data == "blacklist_add")
async def ask_user_to_blacklist(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.delete()
    except Exception:
        pass

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="blacklist_menu")]
    ])

    await callback.message.answer(
        "📝 Введите @юзернейм или ID пользователя для добавления в ЧС:",
        reply_markup=kb
    )
    await state.set_state(BlacklistFSM.waiting_for_user_to_add)

@router.message(BlacklistFSM.waiting_for_user_to_add)
async def ask_blacklist_reason(message: types.Message, state: FSMContext):
    text = message.text.strip()
    tg_id = None
    username_display = text

    if text.startswith("@"):  # username
        username = text[1:]
        async with aiosqlite.connect("data/users.db") as db:
            cursor = await db.execute("SELECT tg_id FROM users WHERE username = ?", (username,))
            row = await cursor.fetchone()
            if row:
                tg_id = row[0]
    elif text.isdigit():
        tg_id = int(text)
        username_display = f"ID: {tg_id}"

    if not tg_id:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="blacklist_menu")]
        ])
        await message.answer("❗ Пользователь не найден. Проверьте ввод.", reply_markup=kb)
        await state.clear()
        return

    # Проверяем, не находится ли уже в ЧС
    blacklist_reason = await is_blacklisted(tg_id)
    if blacklist_reason:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="blacklist_menu")]
        ])
        await message.answer(f"❗ Пользователь {username_display} уже находится в ЧС.\nПричина: {blacklist_reason}", reply_markup=kb)
        await state.clear()
        return

    await state.update_data(tg_id=tg_id, username_display=username_display)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="blacklist_menu")]
    ])

    await message.answer(
        f"📝 Пользователь {username_display} найден.\n\n"
        "Теперь введите причину занесения в ЧС:",
        reply_markup=kb
    )
    await state.set_state(BlacklistFSM.waiting_for_reason)

@router.message(BlacklistFSM.waiting_for_reason)
async def save_to_blacklist(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tg_id = data.get("tg_id")
    username_display = data.get("username_display", f"ID: {tg_id}")
    reason = message.text.strip()

    await add_to_blacklist(tg_id, reason)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Снять ЧС", callback_data=f"blacklist_unban_{tg_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="blacklist_menu")]
    ])

    await message.answer(
        f"✅ Пользователь {username_display} добавлен в ЧС.\n"
        f"📝 Причина: {reason}",
        reply_markup=kb
    )
    await state.clear()

@router.callback_query(F.data.startswith("blacklist_unban_"))
async def unban_user_from_blacklist(callback: types.CallbackQuery):
    """Снимает пользователя с ЧС по кнопке"""
    try:
        tg_id = int(callback.data.split("_")[-1])

        # Получаем информацию о пользователе
        async with aiosqlite.connect("data/users.db") as db:
            cursor = await db.execute("SELECT username FROM users WHERE tg_id = ?", (tg_id,))
            user = await cursor.fetchone()
            username_display = f"@{user[0]}" if user and user[0] else f"ID: {tg_id}"

        # Удаляем из ЧС
        await remove_from_blacklist(tg_id)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="blacklist_menu")]
        ])

        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer(
            f"✅ Пользователь {username_display} снят с ЧС.",
            reply_markup=kb
        )

    except Exception as e:
        await callback.answer("❌ Ошибка при снятии с ЧС")
        logging.error(f"Error removing from blacklist: {e}")

# Старый обработчик удален - теперь используются кнопки "снять ЧС"

@router.callback_query(F.data == "delete_user")
async def ask_user_to_delete(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.delete()
    except Exception:
        pass

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
    ])

    await callback.message.answer(
        "🗑️ <b>Удаление пользователя</b>\n\n"
        "Введите ID или @юзернейм пользователя для полного удаления:\n\n"
        "⚠️ <b>Внимание!</b> Это действие необратимо и удалит:\n"
        "• Профиль пользователя\n"
        "• Весь баланс и историю\n"
        "• Все заявки и заказы\n"
        "• Отзывы и активность\n"
        "• Рефералов и связи",
        parse_mode="HTML",
        reply_markup=kb
    )
    await state.set_state(AdminFSM.waiting_for_user_to_delete)

@router.message(AdminFSM.waiting_for_user_to_delete)
async def process_user_deletion(message: types.Message, state: FSMContext):
    """Обрабатывает ввод пользователя для удаления"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        await state.clear()
        return

    user_input = message.text.strip()

    # Нормализуем поисковый запрос - убираем @ и приводим к нижнему регистру
    if user_input.startswith('@'):
        username = user_input[1:].lower()  # Убираем @ и приводим к нижнему регистру
        search_type = "username"
    elif user_input.isdigit():
        tg_id = int(user_input)
        search_type = "tg_id"
    else:
        username = user_input.lower()  # Приводим к нижнему регистру
        search_type = "username"

    try:
        # Ищем пользователя в базе данных
        async with aiosqlite.connect('data/users.db') as db:
            if search_type == "username":
                cursor = await db.execute('SELECT tg_id, username, full_name, balance FROM users WHERE LOWER(username) = ?', (username,))
            else:
                cursor = await db.execute('SELECT tg_id, username, full_name, balance FROM users WHERE tg_id = ?', (tg_id,))

            user = await cursor.fetchone()

        if not user:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="delete_user")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
            ])

            await message.answer(
                f"❌ Пользователь не найден: {user_input}\n\n"
                "Проверьте правильность ввода.",
                reply_markup=kb
            )
            await state.clear()
            return

        user_tg_id, user_username, user_full_name, user_balance = user
        username_display = f"@{user_username}" if user_username else f"ID: {user_tg_id}"

        # Показываем подтверждение удаления
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑️ Да, удалить", callback_data=f"confirm_delete_user_{user_tg_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
        ])

        await message.answer(
            f"⚠️ <b>Подтверждение удаления</b>\n\n"
            f"<b>Пользователь:</b> {username_display}\n"
            f"<b>Имя:</b> {user_full_name}\n"
            f"<b>Баланс:</b> {user_balance:.2f}₽\n\n"
            f"❗ Вы уверены, что хотите <b>полностью удалить</b> этого пользователя?\n"
            f"Это действие <b>необратимо</b>!",
            parse_mode="HTML",
            reply_markup=kb
        )
        await state.clear()

    except Exception as e:
        logging.error(f"Error in process_user_deletion: {e}")
        await message.answer("❌ Ошибка при поиске пользователя")
        await state.clear()

@router.callback_query(F.data.startswith("confirm_delete_user_"))
async def confirm_user_deletion(callback: types.CallbackQuery):
    """Подтверждает и выполняет удаление пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    try:
        tg_id = int(callback.data.split("_")[-1])

        # Получаем информацию о пользователе перед удалением
        async with aiosqlite.connect('data/users.db') as db:
            cursor = await db.execute('SELECT username, full_name FROM users WHERE tg_id = ?', (tg_id,))
            user = await cursor.fetchone()

        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        username, full_name = user
        username_display = f"@{username}" if username else f"ID: {tg_id}"

        # Удаляем пользователя полностью
        from app.database.models import delete_user_everywhere_full
        delete_user_everywhere_full(tg_id)

        # Также удаляем из черного списка, если есть
        await remove_from_blacklist(tg_id)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
        ])

        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer(
            f"✅ <b>Пользователь удален</b>\n\n"
            f"<b>Удален:</b> {username_display}\n"
            f"<b>Имя:</b> {full_name}\n\n"
            f"🗑️ Все данные пользователя полностью удалены из системы.\n"
            f"При повторном запуске бота пользователь увидит сообщение 'новый пользователь'.",
            parse_mode="HTML",
            reply_markup=kb
        )

        await callback.answer("✅ Пользователь удален")

    except Exception as e:
        logging.error(f"Error in confirm_user_deletion: {e}")
        await callback.answer("❌ Ошибка при удалении пользователя")
        await callback.message.answer("❌ Произошла ошибка при удалении пользователя")

@router.callback_query(F.data == "add_review")
async def admin_add_review(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("✍️ Введите @юзернейм или ID, от кого будет отзыв:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️Назад', callback_data='admin_panel')]]))
    await state.set_state(AddReviewFSM.waiting_for_author)

@router.message(AddReviewFSM.waiting_for_author)
async def receive_review_author(message: types.Message, state: FSMContext):
    author = message.text.strip()
    await state.update_data(review_author=author)
    await message.answer(
        "📨 Теперь отправьте сам отзыв:\n\n"
        "📝 Вы можете отправить:\n"
        "• Только текст\n"
        "• Только фото (в сжатом виде)\n"
        "• Фото с подписью",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️Назад', callback_data='admin_panel')]])
    )
    await state.set_state(AddReviewFSM.waiting_for_content)

@router.message(AddReviewFSM.waiting_for_content)
async def receive_review_content(message: types.Message, state: FSMContext):
    data = await state.get_data()
    author = data.get('review_author', 'Неизвестный автор')

    # Проверяем, что есть хотя бы текст или фото
    if not message.text and not message.photo:
        await message.answer(
            "Пожалуйста, отправьте текст отзыва или фото для отзыва.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️Назад', callback_data='admin_panel')]])
        )
        return

    # Текст может быть пустым, если есть только фото
    review_text = message.text or (message.caption if message.caption else '')

    # Создаем отзыв в базе данных
    photo_file_id = None
    if message.photo and len(message.photo) > 0:
        photo_file_id = message.photo[-1].file_id

    review_id = create_review(
        user_id=0,  # Для админских отзывов используем 0
        content=review_text,
        file_id=photo_file_id,
        status="pending"
    )

    # Отправляем отзыв сразу в канал
    try:
        links = "\n____________________\n🔗 <a href=\"https://t.me/legalstars_bot\">Наш бот</a> | <a href=\"https://t.me/legal_stars\">Наш канал</a>"

        if message.photo and len(message.photo) > 0:
            # Для фото с текстом или без текста
            if review_text.strip():
                caption = f"📝 Новый отзыв от {author}\n\n{review_text}{links}"
            else:
                caption = f"📝 Новый отзыв от {author}{links}"

            await message.bot.send_photo(
                chat_id=REVIEW_CHANNEL_ID,
                photo=photo_file_id,
                caption=caption,
                parse_mode="HTML"
            )
        else:
            # Только текст без фото
            caption = f"📝 Новый отзыв от {author}\n\n{review_text}{links}"
            await message.bot.send_message(
                chat_id=REVIEW_CHANNEL_ID,
                text=caption,
                parse_mode="HTML",
                disable_web_page_preview=True
            )

        # Обновляем статус отзыва
        update_review_status(review_id, status="published")

        await message.answer("✅ Отзыв успешно опубликован в канале!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ В админ панель', callback_data='admin_panel')]]))

    except Exception as e:
        await message.answer(f"❌ Ошибка при публикации отзыва: {e}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ В админ панель', callback_data='admin_panel')]]))

    await state.clear()

@router.callback_query(F.data.startswith("review_publish_"))
async def review_publish(callback: types.CallbackQuery):
    import datetime
    try:
        review_id = int(callback.data.split("_")[2])
        
        from app.database.models import get_review_by_id, update_review_status, get_user_profile_by_id
        review = get_review_by_id(review_id)
        if not review:
            await callback.answer("❌ Отзыв не найден")
            return

        # Получаем информацию о пользователе
        user_profile = get_user_profile_by_id(review['user_id'])
        username = user_profile['username'] if user_profile and user_profile['username'] else None
        
        if not username:
            try:
                tg_user = await callback.bot.get_chat(review['user_id'])
                username = tg_user.username
            except Exception:
                username = None

        author = f"@{username}" if username else f"Пользователь (ID: {review['user_id']})"
        review_text = review['content']

        links = "\n____________________\n🔗 <a href=\"https://t.me/legalstars_bot\">Наш бот</a> | <a href=\"https://t.me/legal_stars\">Наш канал</a>"

        # Формируем caption в зависимости от наличия текста
        if review_text and review_text.strip():
            caption = f"📝 Новый отзыв от {author}\n\n{review_text}{links}"
        else:
            caption = f"📝 Новый отзыв от {author}{links}"

        # Пробуем отправить в канал разными способами
        try:
            # Сначала пробуем по числовому ID
            if review['file_id']:
                await callback.bot.send_photo(
                    chat_id=REVIEW_CHANNEL_ID,
                    photo=review['file_id'],
                    caption=caption,
                    parse_mode="HTML"
                )
            else:
                await callback.bot.send_message(
                    chat_id=REVIEW_CHANNEL_ID,
                    text=caption,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
        except Exception as e:
            # Если не получилось по ID, пробуем по юзернейму
            try:
                if review['file_id']:
                    await callback.bot.send_photo(
                        chat_id=REVIEWS_CHANNEL,  # используем юзернейм
                        photo=review['file_id'],
                        caption=caption,
                        parse_mode="HTML"
                    )
                else:
                    await callback.bot.send_message(
                        chat_id=REVIEWS_CHANNEL,
                        text=caption,
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )
            except Exception as e:
                print(f"Ошибка при публикации отзыва: {e}")
                await callback.answer("❌ Произошла ошибка при публикации отзыва")
                return

        # Обновляем статус отзыва
        update_review_status(review_id, status="published")
        publish_time = datetime.datetime.now().strftime('%H:%M %d.%m.%Y')

        # Удаляем сообщение с кнопкой
        try:
            await callback.message.delete()
        except Exception:
            pass

        # Отправляем подтверждение
        await callback.message.answer(
            f"✅ Отзыв опубликован\n<b>Время публикации:</b> {publish_time}",
            parse_mode="HTML"
        )
        await callback.answer("✅ Отзыв опубликован!")

    except Exception as e:
        print(f"Ошибка при публикации отзыва: {e}")
        await callback.answer("❌ Произошла ошибка при публикации отзыва")


def get_admin_panel_kb(user_id):
    """Формирует клавиатуру админ-панели"""
    if user_id not in ADMINS:
        return None
    
    users_count = len(get_all_users())
    check_flag = get_flag('subscription_check', 'false')
    ref_flag = get_flag('ref_active', 'true')
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"ПРОВЕРКА: {'✅ ВКЛ' if check_flag else '⛔️ ВЫКЛ'}", callback_data="toggle_check")],
        [InlineKeyboardButton(text=f"Рефералы: {'✅ ВКЛ' if ref_flag else '⛔️ ВЫКЛ'}", callback_data="toggle_ref")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")],
        [InlineKeyboardButton(text="🎰 Слот-машина", callback_data="admin_slot_wins")],
        [InlineKeyboardButton(text="📅 Активность", callback_data="admin_activity_stats")],
        [InlineKeyboardButton(text="💬РАССЫЛКА", callback_data="rassilka")],
        [InlineKeyboardButton(text="📂 База данных", callback_data="admin_db")],
        [InlineKeyboardButton(text="🚫 Чёрный список", callback_data="blacklist_menu")],
        [InlineKeyboardButton(text="🗑 Удалить пользователя", callback_data="delete_user")],
        [InlineKeyboardButton(text="➕ Добавить отзыв", callback_data="add_review")],
        [InlineKeyboardButton(text="📋 Все заявки", callback_data="admin_orders")],
        [InlineKeyboardButton(text="🧹 Очистить заявки", callback_data="admin_clear_orders")],
        [InlineKeyboardButton(text="💳 Выводы", callback_data="admin_withdrawals")],
        [InlineKeyboardButton(text="🧹 Очистить выводы", callback_data="admin_clear_withdrawals")],
    ])
    return kb

@router.callback_query(F.data == "admin_panel")
async def back_to_admin_panel(callback: types.CallbackQuery):
    await delete_previous_message(callback)
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Доступ запрещен")
        return
    text, kb = get_admin_panel_text_and_kb_actual()
    try:
        if getattr(callback, 'message', None) and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        else:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        if getattr(callback, 'message', None) and hasattr(callback.message, "answer"):
            await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "add_balance")
async def add_balance_start(callback: types.CallbackQuery, state: FSMContext):
    if getattr(callback, 'message', None) and hasattr(callback.message, "delete"):
        try:
            await callback.message.delete()
        except Exception:
            pass
    # Получаем ID пользователя из предыдущего поиска
    last_message = callback.message.reply_to_message or callback.message
    # Парсим ID из текста сообщения
    import re
    match = re.search(r"ID:\s*(\d+)", last_message.text)
    if not match:
        if getattr(callback, 'message', None) and hasattr(callback.message, "answer"):
            await callback.message.answer("Не удалось определить пользователя. Сначала выполните поиск.")
        return
    user_id = int(match.group(1))
    await state.update_data(user_id=user_id)
    if getattr(callback, 'message', None) and hasattr(callback.message, "answer"):
        await callback.message.answer("💰 Введите сумму для пополнения:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️Назад', callback_data='admin_db')]]))
    await state.set_state(AddBalanceFSM.waiting_for_amount)

@router.message(AddBalanceFSM.waiting_for_amount)
async def receive_amount_for_balance(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        data = await state.get_data()
        user_id = data.get('user_id')
        update_balance(user_id, amount)
        profile = get_user_profile(user_id)
        new_balance = profile['balance'] if profile else 0
        await message.answer(f"✅ Баланс пользователя {user_id} пополнен на {amount:.2f}₽\nНовый баланс: {new_balance:.2f}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️Назад', callback_data='admin_db')]]))
        await state.clear()
    except ValueError:
        await message.answer("❗ Введите корректную сумму.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️Назад', callback_data='admin_db')]]))

@router.callback_query(F.data == "remove_balance")
async def remove_balance_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    # Получаем ID пользователя из предыдущего поиска
    last_message = callback.message.reply_to_message or callback.message
    import re
    match = re.search(r"ID:\s*(\d+)", last_message.text)
    if not match:
        await callback.message.answer("Не удалось определить пользователя. Сначала выполните поиск.")
        return
    user_id = int(match.group(1))
    await state.update_data(user_id=user_id)
    await callback.message.answer("❌ Введите сумму для списания:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️Назад', callback_data='admin_db')]]))
    await state.set_state(RemoveBalanceFSM.waiting_for_amount)

@router.message(RemoveBalanceFSM.waiting_for_amount)
async def receive_amount_for_remove(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        data = await state.get_data()
        user_id = data.get('user_id')
        from app.database.models import remove_balance, get_user_profile
        profile = get_user_profile(user_id)
        if not profile:
            await message.answer("Пользователь не найден.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️Назад', callback_data='admin_db')]]))
            await state.clear()
            return
        balance = profile['balance']
        if amount > balance:
            await message.answer(f"❗ Недостаточно средств. Баланс пользователя: {balance:.2f}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️Назад', callback_data='admin_db')]]))
            await state.clear()
            return
        remove_balance(user_id, amount)
        profile = get_user_profile(user_id)
        new_balance = profile['balance'] if profile else 0
        await message.answer(f"✅ С баланса пользователя {user_id} списано {amount:.2f}₽\nНовый баланс: {new_balance:.2f}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️Назад', callback_data='admin_db')]]))
        await state.clear()
    except ValueError:
        await message.answer("❗ Введите корректную сумму.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️Назад', callback_data='admin_db')]]))

@router.callback_query(F.data == "remove_balance_confirm")
async def remove_balance_confirm(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('user_id')
    amount = data.get('amount')
    from app.database.models import remove_balance, get_user_profile
    remove_balance(user_id, amount)
    profile = get_user_profile(user_id)
    new_balance = profile['balance'] if profile else 0
    await callback.message.answer(f"✅ С баланса пользователя {user_id} списано {amount:.2f}₽.\nНовый баланс: {new_balance:.2f}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️Назад', callback_data='admin_panel')]]))
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass

# Обработчик кнопки "Назад" в меню криптовалют из состояния ожидания PDF
@router.callback_query(CryptoPayStates.waiting_receipt_pdf, F.data == "crypto")
async def crypto_menu_from_pdf_state(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await crypto_menu(call)

@router.callback_query(F.data == "crypto")
async def crypto_menu(call: types.CallbackQuery):
    await delete_previous_message(call)

    # Проверяем черный список
    if await check_blacklist_and_respond(call.from_user.id, call):
        return

    # Проверка подписки (только если включена в настройках)
    from app.config_flags import proverka
    if proverka and not await check_subscription(call.from_user.id, call.bot):
        await show_subscription_message(call, call.bot)
        return
        
    crypto_photo = get_admin_setting('crypto_photo', 'https://imgur.com/a/3ZZOHNJ.jpeg')
    crypto_description = get_admin_setting('crypto_description', 'Теперь у нас вы можете приобрести криптовалюту за рубли!\n\nЛегко, быстро и безопасно — просто выберите нужный раздел, а всё остальное сделаем мы за вас.\n\n🔐 Ваша безопасность и конфиденциальность гарантированы.');
    kb = crypto_menu_inline_kb()
    await call.message.answer_photo(
        photo=crypto_photo,
        caption=crypto_description,
        reply_markup=kb
    )

@router.callback_query(F.data == "crypto_ton")
async def crypto_ton(call: types.CallbackQuery, state: FSMContext):
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer(
        "Введите желаемое количество TON, которое хотите купить (можно дробное число):\n🔻 Минимум для покупки: 0.2 TON",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto")]]
        )
    )
    await state.set_state(CryptoStates.waiting_ton)

@router.callback_query(F.data == "crypto_not")
async def crypto_not(call: types.CallbackQuery, state: FSMContext):
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer(
        "Введите желаемое количество NOT, которое хотите купить (целое число):\n🔻 Минимум для покупки: 500 NOT",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto")]]
        )
    )
    await state.set_state(CryptoStates.waiting_not)

@router.callback_query(F.data == "crypto_dogs")
async def crypto_dogs(call: types.CallbackQuery, state: FSMContext):
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer(
        "Введите желаемое количество DOGS, которое хотите купить (целое число):\n🔻 Минимум для покупки: 5000 DOGS",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto")]]
        )
    )
    await state.set_state(CryptoStates.waiting_dogs)

@router.message(CryptoStates.waiting_ton)
async def process_ton_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
    except ValueError:
        await message.answer("Пожалуйста, введите число!", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto")]]))
        return
    if amount < 0.2:
        await message.answer("Минимум для покупки: 0.2 TON", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto")]]))
        return
    price_rub = await get_crypto_rub_price('TON')
    total = amount * price_rub * 1.20  # +20%
    await state.update_data(coin='TON', amount=amount, total=total)
    text = f"💱 Вы хотите купить {amount} TON\n💰 Сумма покупки: {total:.6f} RUB\n\nПродолжить покупку?"
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ Продолжить", callback_data="crypto_confirm"), types.InlineKeyboardButton(text="❌ Отменить", callback_data="crypto")],
        ]
    )
    await message.answer(text, reply_markup=kb)
    # Состояние будет установлено после нажатия "Продолжить"

@router.message(CryptoStates.waiting_not)
async def process_not_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("Пожалуйста, введите целое число!", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto")]]))
        return
    if amount < 500:
        await message.answer("Минимум для покупки: 500 NOT", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto")]]))
        return
    price_rub = await get_crypto_rub_price('NOT')
    total = amount * price_rub * 1.18  # +18%
    await state.update_data(coin='NOT', amount=amount, total=total)
    text = f"💱 Вы хотите купить {amount} NOT\n💰 Сумма покупки: {total:.6f} RUB\n\nПродолжить покупку?"
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ Продолжить", callback_data="crypto_confirm"), types.InlineKeyboardButton(text="❌ Отменить", callback_data="crypto")],
        ]
    )
    await message.answer(text, reply_markup=kb)
    # Состояние будет установлено после нажатия "Продолжить"

@router.message(CryptoStates.waiting_dogs)
async def process_dogs_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("Пожалуйста, введите целое число!", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto")]]))
        return
    if amount < 5000:
        await message.answer("💸 Введите сумму для вывода (минимум 500₽):", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]]))
        return
    price_rub = await get_crypto_rub_price('DOGS')
    total = amount * price_rub * 1.15  # +15%
    await state.update_data(coin='DOGS', amount=amount, total=total)
    text = f"💱 Вы хотите купить {amount} DOGS\n💰 Сумма покупки: {total:.6f} RUB\n\nПродолжить покупку?"
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ Продолжить", callback_data="crypto_confirm"), types.InlineKeyboardButton(text="❌ Отменить", callback_data="crypto")],
        ]
    )
    await message.answer(text, reply_markup=kb)
    # Состояние будет установлено после нажатия "Продолжить"

@router.callback_query(F.data == "crypto_confirm")
async def crypto_confirm(call: types.CallbackQuery, state: FSMContext):
    try:
        await call.message.delete()
    except Exception:
        pass

    data = await state.get_data()
    coin = data.get('coin', '?')
    amount = data.get('amount', '?')
    total = data.get('total', 0.0)

    # Если данных нет (состояние было очищено), возвращаем в меню криптовалют
    if not data or coin == '?' or amount == '?' or total == 0.0:
        await crypto_menu(call)
        return

    text = (
        f"<b>Оплатите {total:.2f}₽ за {amount} {coin}</b>\n"
        f"По номеру: <code>+79912148689</code> (кликабельно для копирования)\n"
        f"Банк: <i>Альфа-Банк</i>\n\n"
        f"После оплаты нажмите кнопку ниже, чтобы загрузить чек"
    )

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🧾 Загрузить чек", callback_data="crypto_upload_receipt")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto")],
        ]
    )

    await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(CryptoPayStates.waiting_receipt_pdf)

@router.callback_query(F.data == "crypto_upload_receipt")
async def crypto_upload_receipt_start(call: types.CallbackQuery, state: FSMContext):
    try:
        await call.message.delete()
    except Exception:
        pass
    
    text = (
        "💬 Отправьте файл с чеком (PDF формат - обязательно) для проверки администрацией:\n\n"
        "❗ Требования к чеку:\n"
        "- Формат: PDF\n"
        "- Макс. размер: 5MB\n"
        "- Чек должен быть читаемым"
    )
    
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto_confirm")],
        ]
    )
    
    await call.message.answer(text, reply_markup=kb)
    await state.set_state(CryptoPayStates.waiting_receipt_pdf)

@router.message(CryptoPayStates.waiting_receipt_pdf, F.document)
async def crypto_handle_pdf_receipt(message: types.Message, state: FSMContext):
    # Проверяем, что файл - PDF
    file_name = message.document.file_name or ""
    if not file_name.lower().endswith('.pdf'):
        await message.answer(
            "❌ Неверный формат чека. Пожалуйста, отправляйте только файлы в формате PDF.\n"
            "Попробуйте ещё раз, но уже с форматом PDF.\n"
            "Если у вас возникнут вопросы, не стесняйтесь связаться со мной."
        )
        return

    # Проверка размера файла (максимум 5MB)
    if message.document.file_size > 5 * 1024 * 1024:
        error_text = (
            "❌ Файл слишком большой. Максимальный размер - 5MB.\n\n"
            "Пожалуйста, сожмите файл или отправьте другой чек.\n\n"
            "Если у вас не получается, обратитесь в поддержку:"
        )
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="📩 Связаться с поддержкой", url="https://t.me/Black_Prince01")],
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto_confirm")],
            ]
        )
        await message.answer(error_text, reply_markup=kb)
        return

    # Сохраняем file_id чека
    await state.update_data(
        receipt_file_id=message.document.file_id,
        receipt_file_name=file_name or "receipt.pdf"
    )

    # Запрашиваем кошелёк
    await message.answer(
        "✅ Чек получен! Теперь укажите адрес кошелька для получения криптовалюты:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto_upload_receipt")]
        ])
    )
    await state.set_state(CryptoPayStates.waiting_wallet)

@router.message(CryptoPayStates.waiting_wallet)
async def crypto_process_wallet(message: types.Message, state: FSMContext):
    # Получаем данные из состояния
    data = await state.get_data()
    wallet = (message.text or '').strip()
    
    if not wallet:
        await message.answer("Пожалуйста, введите адрес кошелька.")
        return
    
    # Получаем database ID пользователя
    user_profile = get_user_profile(message.from_user.id)
    if not user_profile:
        await message.answer("❌ Ошибка: пользователь не найден в базе данных.")
        await state.clear()
        return

    # Создаем заказ в базе данных
    order_id = create_order(
        user_id=user_profile['id'],  # Используем database ID
        order_type="crypto",
        amount=data.get('total', 0),
        status="pending",
        file_id=data.get('receipt_file_id'),
        extra_data={
            'coin': data.get('coin', ''),
            'amount': data.get('amount', 0),
            'wallet': wallet
        }
    )

    # Формируем текст сообщения
    order_info = (
        f"🌟 <b>НОВЫЙ ЗАКАЗ TELEGRAM PREMIUM</b> 🌟\n\n"
        f"👤 <b>Клиент:</b> @{message.from_user.username or message.from_user.id}\n"
        f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
        f"📦 <b>Монета:</b> {data.get('coin', '?')}\n"
        f"⏳ <b>Количество:</b> {data.get('amount', '?')}\n"
        f"💵 <b>Стоимость:</b> {data.get('total', '?')}₽\n"
        f"🔑 <b>Кошелек:</b> {wallet}\n"
        f"🕒 <b>Дата/время:</b> {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        f"📌 <b>Номер заказа:</b> <code>{order_id}</code>\n\n"
        f"#заказ #{order_id}"
    )

    # Создаем клавиатуру для админов
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"order_pay_{order_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"order_reject_{order_id}"),
        ],
        [
            InlineKeyboardButton(text="🗑 Удалить заказ", callback_data=f"order_delete_{order_id}")
        ]
    ])

    # Отправляем информацию админам
    try:
        for admin_id in ADMINS:
            try:
                if data.get('receipt_file_id'):
                    # Отправляем сообщение с прикрепленным чеком
                    admin_msg = await message.bot.send_document(
                        chat_id=admin_id,
                        document=data.get('receipt_file_id'),
                        caption=order_info,
                        reply_markup=admin_kb,
                        parse_mode="HTML"
                    )
                else:
                    # Если чека нет, отправляем просто текст
                    admin_msg = await message.bot.send_message(
                        chat_id=admin_id,
                        text=order_info,
                        reply_markup=admin_kb,
                        parse_mode="HTML"
                    )
                
                # Обновляем ID сообщения в базе данных
                if admin_id == ADMINS[0]:  # Сохраняем ID только первого сообщения
                    update_order_status(order_id, admin_msg_id=admin_msg.message_id)
                
            except Exception as admin_error:
                logging.error(f"Ошибка отправки заказа админу {admin_id}: {admin_error}")
                continue

    except Exception as e:
        logging.error(f"Критическая ошибка при обработке заказа: {e}")
        await message.answer(
            "⚠️ Произошла ошибка при отправке заказа. Пожалуйста, попробуйте позже.",
            reply_markup=main_menu_inline_kb()
        )
        return

    # Отправляем подтверждение пользователю
    await message.answer(
        "✅ Ваш заказ на криптовалюту успешно отправлен на проверку!\n\n"
        "Администратор проверит ваш чек и отправит криптовалюту в ближайшее время.",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🛍️ Оставить отзыв", callback_data="leave_review")],
            [types.InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")],
        ])
    )
    
    # Очищаем состояние
    await state.clear()

@router.callback_query(F.data == "crypto_other")
async def crypto_other(call: types.CallbackQuery):
    try:
        await call.message.delete()
    except Exception:
        pass
    
    text = (
        "💬 Напишите в поддержку, чтобы узнать о покупке других криптовалют!\n\n"
        "Мы работаем с TON, NOT, DOGS и другими популярными монетами."
    )
    
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="💬 Написать в поддержку", url="https://t.me/Black_Prince01")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto")],
        ]
    )
    
    await call.message.answer(text, reply_markup=kb)

async def get_crypto_rub_price(symbol):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT') as resp:
            data = await resp.json()
            price_usdt = float(data['price'])
        async with session.get('https://www.cbr-xml-daily.ru/daily_json.js') as resp:
            text = await resp.text()
            data = json.loads(text)
            usd_rub = float(data['Valute']['USD']['Value'])
        price_rub = price_usdt * usd_rub
        return price_rub

@router.callback_query(F.data == "stars")
async def stars_menu(call: types.CallbackQuery):
    await delete_previous_message(call)

    # Проверяем черный список
    if await check_blacklist_and_respond(call.from_user.id, call):
        return

    # Используем единую функцию проверки подписки
    if not await check_subscription_required(call.from_user.id, call.bot):
        await show_subscription_message(call, call.bot)
        return
        
    # Остальной код обработчика...
        
    stars_photo = get_admin_setting('stars_photo', 'https://imgur.com/a/0Tx7psa.jpeg')
    stars_description = get_admin_setting('stars_description', '''
🌟 Добро пожаловать в раздел покупки звёзд!

Здесь вы можете выбрать звёзды для разных случаев: подарок, награда или просто для себя.

✨ Как это работает?
1️⃣ Выберите количество звёзд
2️⃣ Оплатите любым удобным способом

🔒 Гарантируем безопасность и легальность сделок.
''')
    if not stars_description:
        stars_description = '''
🌟 Добро пожаловать в раздел покупки звёзд!

Здесь вы можете выбрать звёзды для разных случаев: подарок, награда или просто для себя.

✨ Как это работает?
1️⃣ Выберите количество звёзд
2️⃣ Оплатите любым удобным способом

🔒 Гарантируем безопасность и легальность сделок.
'''
    kb = stars_menu_inline_kb()
    await call.message.answer_photo(
        photo=stars_photo,
        caption=stars_description,
        reply_markup=kb,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "withdraw")
async def withdraw_start(call: types.CallbackQuery, state: FSMContext):
    profile = get_user_profile(call.from_user.id)
    if not profile:
        await call.message.answer("Профиль не найден.", reply_markup=main_menu_inline_kb())
        return
    balance = profile['balance']
    await state.update_data(back_to="profile")
    
    # Проверяем баланс пользователя
    if balance < 500:
        # Сообщение профиля не удаляем! Просто отправляем отдельное сообщение
        await call.message.answer("❗ Недостаточно средств для минимального вывода (минимум 500₽)")
        return
    
    # Если баланс больше или равен 500 рублей - удаляем профиль и запрашиваем сумму для вывода
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer("💸 Введите сумму для вывода (минимум 500₽):", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]]))
    await state.set_state(WithdrawStates.waiting_amount)

@router.message(WithdrawStates.waiting_amount)
async def withdraw_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
    except Exception:
        await message.answer("Введите корректную сумму.", reply_markup=back_to_profile_kb())
        return

    # Получаем баланс из базы
    async with aiosqlite.connect("data/users.db") as db:
        cursor = await db.execute("SELECT balance FROM users WHERE tg_id = ?", (message.from_user.id,))
        result = await cursor.fetchone()
        if not result:
            await message.answer("Пользователь не найден.", reply_markup=back_to_profile_kb())
            return
        balance = result[0]

    # Проверяем минимальную сумму для вывода
    if amount < 500:
        await message.answer("❗ Минимальная сумма для вывода — 500₽", reply_markup=back_to_profile_kb())
        return
    
    # Проверяем достаточность средств на балансе
    if amount > balance:
        await message.answer("❗ Недостаточно средств на балансе.", reply_markup=back_to_profile_kb())
        return

    await state.update_data(amount=amount)
    await message.answer(f"⚠️ Вы уверены, что хотите вывести {amount:.2f}₽? Эта сумма будет заморожена до подтверждения администратором.", reply_markup=withdraw_confirm_kb())
    await state.set_state(WithdrawStates.confirm)

@router.callback_query(F.data == "withdraw_confirm")
async def withdraw_confirm(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount = data.get("amount")
    if not amount:
        await call.message.answer("Ошибка. Попробуйте снова.", reply_markup=main_menu_inline_kb())
        await state.clear()
        return
    
    text = ("💳 Укажите свои реквизиты — куда нужно выводить средства.\n"
            "⚠️ Обратите внимание: деньги выводятся на банки РФ.\n"
            "🌍 Если у вас банк другой страны, пожалуйста, свяжитесь с поддержкой для получения инструкции.\n\n"
            "Спасибо за сотрудничество! 😊")
    
    await call.message.answer(text, reply_markup=withdraw_requisites_kb())
    await state.set_state(WithdrawStates.waiting_requisites)

@router.message(WithdrawStates.waiting_requisites)
async def withdraw_requisites(message: types.Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("amount")
    requisites = (message.text or '').strip()
    
    if not amount:
        await message.answer("❌ Ошибка: сумма не найдена. Попробуйте снова.", reply_markup=main_menu_inline_kb())
        await state.clear()
        return
    
    # Получаем профиль пользователя из базы данных
    user_profile = get_user_profile(message.from_user.id)
    if not user_profile:
        await message.answer("❌ Ошибка: профиль не найден.", reply_markup=main_menu_inline_kb())
        await state.clear()
        return
    
    user_id = user_profile['id']  # ID в базе данных
    commission = round(amount * 0.03, 2)
    final_amount = round(amount - commission, 2)
    
    # Замораживаем средства
    freeze_balance(message.from_user.id, amount)
    
    # Создаем заявку на вывод
    order_id = create_order(
        user_id=user_id,  # Используем ID из базы данных
        order_type="withdraw",
        amount=amount,
        status="pending",
        file_id=None,
        extra_data={
            "requisites": requisites,
            "commission": commission,
            "final_amount": final_amount
        }
    )
    
    await message.answer("✅ Заявка на вывод отправлена. Ожидайте подтверждения администратора.", reply_markup=main_menu_inline_kb())
    
    author_link = f"@{message.from_user.username or message.from_user.id}" if (message.from_user.username or message.from_user.id) else f"ID: {message.from_user.id}"
    text = (
        f"🔔 Запрос на вывод средств:\n"
        f"👤 Пользователь: {author_link}\n"
        f"📊 Сумма запроса: <b>{amount:.2f}₽</b>\n"
        f"💳 Комиссия (3%): <b>{commission:.2f}₽</b>\n"
        f"💰 К выплате: <b>{final_amount:.2f}₽</b>\n"
        f"💳 Реквизиты: {requisites}\n"
        f"⏰ Время: {datetime.datetime.now().strftime('%H:%M %d.%m.%Y')}\n"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Выплатить", callback_data=f"order_pay_{order_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"order_reject_{order_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"order_delete_{order_id}")]
    ])
    try:
        admin_msgs = await send_to_admins(
            message.bot,
            text,
            reply_markup=markup,
            parse_mode="HTML"
        )
        if admin_msgs:
            update_order_status(order_id, admin_msg_id=admin_msgs[0][1])
    except Exception as e:
        print(f"[ERROR][WITHDRAW] Не удалось отправить чек админу: {e}")
    await state.clear()

@router.callback_query(lambda c: c.data.startswith("withdraw_reject_"))
async def withdraw_reject(callback: types.CallbackQuery):
    try:
        parts = callback.data.split("_")
        withdrawal_id = int(parts[2])
        user_id = int(parts[3])
        amount = float(parts[4])
    except Exception:
        await callback.answer("Ошибка данных.")
        await callback.message.edit_text("❌ Заявка на вывод отклонена.")
        return
    
    # Обновляем статус заявки
    from app.database.models import update_withdrawal_status
    update_withdrawal_status(withdrawal_id, 'rejected')
    
    # Возвращаем замороженные средства
    unfreeze_balance(user_id, amount)
    
    # Оповещаем пользователя
    try:
        await callback.bot.send_message(user_id, f"❌ Ваша заявка на вывод {amount:.2f}₽ отклонена. Средства возвращены на баланс.")
    except Exception:
        pass
    
    await callback.answer("❌ Заявка на вывод отклонена.")
    await callback.message.edit_text("❌ Заявка на вывод отклонена.")

@router.callback_query(lambda c: c.data.startswith("withdraw_delete_"))
async def withdraw_delete(callback: types.CallbackQuery):
    try:
        parts = callback.data.split("_")
        withdrawal_id = int(parts[2])
    except Exception:
        await callback.answer("Ошибка данных.")
        await callback.message.edit_text("🗑 Заявка удалена.")
        return
    
    # Получаем информацию о заявке
    from app.database.models import get_withdrawal_by_id
    withdrawal = get_withdrawal_by_id(withdrawal_id)
    
    if withdrawal:
        user_id = withdrawal[6]  # tg_id
        amount = withdrawal[2]
        status = withdrawal[3]
        
        # Если заявка была в статусе pending, возвращаем средства
        if status == 'pending':
            unfreeze_balance(user_id, amount)
        
        # Удаляем заявку из базы
        import sqlite3
        conn = sqlite3.connect('data/users.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM withdrawals WHERE id = ?', (withdrawal_id,))
        conn.commit()
        conn.close()
    
    await callback.answer("🗑 Заявка удалена.")
    await callback.message.edit_text("🗑 Заявка удалена.")

# Команда для полной очистки истории заявок и замороженных средств (только для админа)
from aiogram.filters import Command
@router.message(Command("clear_withdrawals"))
async def clear_withdrawals_command(message: types.Message):
    admin_ids = [829887947, 6782740295]  # Список ID админов
    if message.from_user.id not in admin_ids:
        await message.answer("Нет доступа.")
        return
    clear_all_withdrawals_and_frozen()
    await message.answer("✅ История заявок и замороженные средства полностью очищены.")

@router.message(Command("clear_calendar"))
async def clear_calendar_command(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.answer("Нет доступа.")
        return
    from app.database.models import clear_all_calendar_data, clear_all_activity_prizes
    success1 = clear_all_calendar_data()
    success2 = clear_all_activity_prizes()
    if success1 and success2:
        await message.answer("✅ Все данные календаря активности очищены:\n• История активности пользователей\n• Все призы активности\n\n💡 Для восстановления призов используйте /reset_prizes")
    else:
        await message.answer("❌ Ошибка при очистке данных календаря.")

@router.message(Command("clear_slot"))
async def clear_slot_command(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.answer("Нет доступа.")
        return
    from app.database.models import clear_all_slot_data, clear_all_slot_prizes
    success1 = clear_all_slot_data()
    success2 = clear_all_slot_prizes()
    if success1 and success2:
        await message.answer("✅ Все данные слот-машины очищены:\n• История выигрышей\n• Счетчики использованных спинов\n• Статусы историй\n• Даты сброса спинов\n• Все призы слот-машины\n\n💡 Для восстановления призов используйте /reset_prizes")
    else:
        await message.answer("❌ Ошибка при очистке данных слот-машины.")

@router.message(Command("reset_prizes"))
async def reset_prizes_command(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.answer("Нет доступа.")
        return
    from app.database.models import reset_all_prizes
    success = reset_all_prizes()
    if success:
        await message.answer("✅ Все призы переинициализированы:\n• Призы слот-машины восстановлены\n• Призы активности восстановлены\n\n🎰 Слот-машина готова к работе!\n📅 Календарь активности готов к работе!")
    else:
        await message.answer("❌ Ошибка при переинициализации призов.")

def get_last_withdraw_orders(tg_id, limit=5):
    import sqlite3
    conn = sqlite3.connect('data/users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE tg_id=?', (tg_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return []
    user_id = user[0]
    cursor.execute('''SELECT amount, status, created_at FROM orders WHERE user_id=? AND type="withdraw" ORDER BY created_at DESC LIMIT ?''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

@router.callback_query(F.data == "profile")
async def profile_menu(call: types.CallbackQuery, bot: Bot, state: FSMContext):
    await delete_previous_message(call)
    """Обработчик меню профиля с проверкой подписки"""

    # Проверяем черный список
    if await check_blacklist_and_respond(call.from_user.id, call):
        return

    # Проверяем подписку (если требуется)
    if not await check_subscription(call.from_user.id, bot):
        await show_subscription_message(call, bot)
        return

    try:
        # Получаем данные пользователя
        user = get_user_profile(call.from_user.id)
        if not user:
            await call.message.answer(
                "Профиль не найден.", 
                reply_markup=main_menu_inline_kb()
            )
            return

        # Форматируем данные
        balance = float(user['balance'] or 0)
        frozen = float(user['frozen'] or 0)
        reg_date = user['reg_date'] or "не указана"
        
        # Получаем настройки профиля из админ панели
        profile_description = get_admin_setting('profile_description', '🚀 <b>Ваш профиль</b>\n\nЗдесь вы можете посмотреть информацию о своем аккаунте, балансе и истории операций.')
        profile_photo = get_admin_setting('profile_photo', 'https://imgur.com/a/TkOPe7c.jpeg')

        # Формируем текст
        text = (
            f"{profile_description}\n\n"
            f"🆔 <b>ID:</b> <a href='tg://user?id={user['tg_id']}'>{user['tg_id']}</a>\n"
            f"📅 <b>Регистрация:</b> {reg_date}\n"
            f"💰 <b>Баланс:</b> {balance:.2f}₽\n"
            f"❄️ <b>Заморожено:</b> {frozen:.2f}₽\n"
        )

        # Добавляем реферальную информацию, если включено
        if ref_active:
            from app.database.models import get_unclaimed_referrals_count

            referrals = get_referrals_count(user['tg_id'])
            bot_username = (await bot.me()).username
            ref_link = f"https://t.me/{bot_username}?start=ref_{user['tg_id']}"

            # Получаем количество неактивированных рефералов
            try:
                unclaimed_count = await get_unclaimed_referrals_count(user['id'])
            except Exception as e:
                logging.error(f"Ошибка получения неактивированных рефералов: {e}")
                unclaimed_count = 0

            text += (
                f"\n👥 <b>Приглашено:</b> {referrals} пользователей\n"
                f"🎁 <b>Неактивированных:</b> {unclaimed_count} рефералов\n"
                f"🔗 <b>Реферальная ссылка:</b>\n<code>{ref_link}</code>\n"
            )

            if unclaimed_count > 0:
                text += f"\n💡 У вас есть {unclaimed_count} неактивированных рефералов! Активируйте их в слот-машине для получения бонусных попыток.\n"

        # Создаем клавиатуру
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📤 Вывести средства", 
                        callback_data="withdraw"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад", 
                        callback_data="main_menu"
                    )
                ]
            ]
        )

        # Удаляем предыдущее сообщение и отправляем новое с фото
        try:
            await call.message.delete()
        except:
            pass

        await call.message.answer_photo(
            photo=profile_photo,
            caption=text,
            reply_markup=kb,
            parse_mode="HTML"
        )

    except Exception as e:
        logging.error(f"Ошибка в профиле пользователя {call.from_user.id}: {e}")
        await call.message.answer(
            "⚠️ Произошла ошибка при загрузке профиля. Попробуйте позже.",
            reply_markup=main_menu_inline_kb()
        )

# --- Обработка выбора фиксированного количества звёзд ---
@router.callback_query(lambda c: c.data.startswith("stars_") and c.data[6:].isdigit() and not c.data.startswith("stars_pay_"))
async def stars_fixed_amount(call: types.CallbackQuery, state: FSMContext):
    try:
        await call.message.delete()
    except Exception:
        pass
    prices = {
        50: 85, 75: 127, 100: 165, 150: 248, 200: 340, 250: 413, 350: 578, 500: 825, 700: 1155, 1000: 1640
    }
    amount = int(call.data.replace("stars_", ""))
    price = prices.get(amount)
    if not price:
        await call.message.answer("❌ Неверное количество звезд", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="stars")]]))
        return
    text = f"Вы выбрали <b>{amount}⭐</b> на сумму <b>{price} RUB</b>. Выберите способ оплаты:"
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="📱 СБП", callback_data=f"stars_pay_sbp_{amount}_{price}"), types.InlineKeyboardButton(text="💰 Криптовалюта", callback_data=f"stars_pay_crypto_{amount}_{price}")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="stars")],
        ]
    )
    await call.message.answer(text, reply_markup=kb, parse_mode="HTML")

# --- Оплата криптовалютой (Premium) ---
@router.callback_query(F.data.startswith("pay_crypto_"))
async def pay_crypto_premium_menu(call: types.CallbackQuery):
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer(
        "💰 Оплата криптовалютой?\n\nЕсли вы хотите использовать криптовалюту для оплаты, просто напишите мне в личные сообщения! Мы обсудим все детали и найдем оптимальное решение для вас.\n\n🌟 Жду вашего сообщения!",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="💬 Написать в поддержку", url="https://t.me/Black_Prince01")],
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="tg_premium")],
            ]
        )
    )

# --- Оплата криптовалютой (звёзды) ---
@router.callback_query(F.data.startswith("stars_pay_crypto_"))
async def stars_pay_crypto_menu(call: types.CallbackQuery):
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer(
        "💰 Оплата криптовалютой?\n\nЕсли вы хотите использовать криптовалюту для оплаты, просто напишите мне в личные сообщения! Мы обсудим все детали и найдем оптимальное решение для вас.\n\n🌟 Жду вашего сообщения!",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="💬 Написать в поддержку", url="https://t.me/Black_Prince01")],
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="stars")],
            ]
        )
    )

# --- Выбор криптовалюты и ввод количества ---
@router.callback_query(lambda c: c.data.startswith("crypto_ton") or c.data.startswith("crypto_not") or c.data.startswith("crypto_dogs"))
async def crypto_choose_amount(call: types.CallbackQuery, state: FSMContext):
    try:
        await call.message.delete()
    except Exception:
        pass
    if call.data == "crypto_ton":
        await call.message.answer("Введите количество TON (минимум 0.2):", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto")]]))
        await state.set_state(CryptoStates.waiting_ton)
    elif call.data == "crypto_not":
        await call.message.answer("Введите количество NOT (минимум 500):", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto")]]))
        await state.set_state(CryptoStates.waiting_not)
    elif call.data == "crypto_dogs":
        await call.message.answer("Введите количество DOGS (минимум 5000):", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="crypto")]]))
        await state.set_state(CryptoStates.waiting_dogs)

# --- Другое количество звёзд ---
@router.callback_query(F.data == "stars_custom")
async def stars_custom_amount(call: types.CallbackQuery, state: FSMContext):
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer(
        "Введите количество звезд\nОбратите внимание,при покупке меньше 50 единиц доступно только КРАТНОЕ 13 звездам (подарок за 15 звезд можно продать за 13) и КРАТНОЕ 21 звездам\n✨ При покупке от 50 звёзд я  отправлю вам любое количество звезд без комиссии",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="stars")],
            ]
        )
    )
    await state.set_state(PremiumStates.waiting_custom_stars)

@router.message(PremiumStates.waiting_custom_stars)
async def process_custom_stars(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("Пожалуйста, введите число!", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="stars")]]))
        return
    fixed = {13: 15, 21: 25, 26: 30, 34: 40, 39: 45, 42: 50}
    if amount < 50:
        if amount not in fixed:
            await message.answer(f"Недопустимое количество. Доступно: {', '.join(map(str, fixed.keys()))} или от 50.", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="stars")]]))
            return
        price = round(fixed[amount] * 1.65)
    elif 50 <= amount < 1500:
        price = round(amount * 1.65)
    elif amount >= 1500:
        price = round(amount * 1.6)
    else:
        await message.answer("Недопустимое количество.", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="stars")]]))
        return
    text = f"Вы выбрали <b>{amount}⭐</b> на сумму <b>{price} RUB</b>. Выберите способ оплаты:"
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="💸 СБП", callback_data=f"stars_pay_sbp_{amount}_{price}"), types.InlineKeyboardButton(text="💰 Криптовалюта", callback_data=f"stars_pay_crypto_{amount}_{price}")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="stars")],
        ]
    )
    await message.answer(text, reply_markup=kb)
    await state.clear()

# --- Оплата звёзд через СБП ---
@router.callback_query(F.data.startswith("stars_pay_sbp_"))
async def stars_pay_sbp_menu(call: types.CallbackQuery, state: FSMContext):
    try:
        # Очищаем предыдущее состояние
        await state.clear()
        
        parts = call.data.replace("stars_pay_sbp_", "").split("_")
        amount, price = int(parts[0]), int(parts[1])
        
        await state.update_data(stars_amount=amount, stars_price=price)
        
        text = (
            f"<b>Оплатите {price}₽ за {amount}⭐</b>\n"
            f"По номеру: <code>+79912148689</code> (кликабельно для копирования)\n"
            f"Банк: <i>Альфа-Банк</i>\n\n"
            f"После оплаты нажмите кнопку ниже, чтобы загрузить чек"
        )
        
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="🧾 Загрузить чек", callback_data=f"stars_upload_receipt_{amount}_{price}")],
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="stars")],
            ]
        )
        
        try:
            await call.message.delete()
        except:
            pass
            
        await call.message.answer(text, reply_markup=kb)
        
    except Exception as e:
        logging.error(f"Error in stars_pay_sbp_menu: {e}")
        await call.answer("⚠️ Произошла ошибка. Попробуйте еще раз.")

@router.callback_query(F.data.startswith("stars_upload_receipt_"))
async def stars_upload_receipt_start(call: types.CallbackQuery, state: FSMContext):
    try:
        if getattr(call, 'message', None) and hasattr(call.message, "delete"):
            await call.message.delete()
    except Exception:
        pass
    
    parts = call.data.replace("stars_upload_receipt_", "").split("_")
    amount, price = int(parts[0]), int(parts[1])
    await state.update_data(stars_amount=amount, stars_price=price)
    
    text = (
        "💬 Отправьте файл с чеком (PDF формат - обязательно) для проверки администрацией:\n\n"
        "❗ Требования к чеку:\n"
        "- Формат: PDF\n"
        "- Макс. размер: 5MB\n"
        "- Чек должен быть читаемым"
    )
    
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"stars_pay_sbp_{amount}_{price}")],
        ]
    )
    
    if getattr(call, 'message', None) and hasattr(call.message, "answer"):
        await call.message.answer(text, reply_markup=kb)
    
    await state.set_state(StarsStates.waiting_receipt_pdf)

@router.message(StarsStates.waiting_receipt_pdf, F.document)
async def stars_handle_pdf_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not data or 'stars_amount' not in data or 'stars_price' not in data:
        await state.clear()
        await message.answer("❌ Сессия истекла. Начните процесс заново.")
        return
    
    amount = data['stars_amount']
    price = data['stars_price']
    
    # Проверка формата файла
    file_name = message.document.file_name or ""
    if not file_name.lower().endswith('.pdf'):
        error_text = (
            "❌ Неверный формат чека. Пожалуйста, отправляйте только файлы в формате PDF.\n"
            "Попробуйте ещё раз, но уже с форматом PDF.\n"
            "Если у вас возникнут вопросы, не стесняйтесь связаться со мной."
        )
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="📩 Связаться с поддержкой", url="https://t.me/Black_Prince01")],
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"stars_pay_sbp_{amount}_{price}")],
            ]
        )
        await message.answer(error_text, reply_markup=kb)
        return
    
    # Проверка размера файла (максимум 5MB)
    if message.document.file_size > 5 * 1024 * 1024:
        error_text = (
            "❌ Файл слишком большой. Максимальный размер - 5MB.\n"
            "Пожалуйста, сожмите файл или отправьте другой чек.\n\n"
            "Если у вас не получается, обратитесь в поддержку:"
        )
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="📩 Связаться с поддержкой", url="https://t.me/support_username")],
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"stars_pay_sbp_{amount}_{price}")],
            ]
        )
        await message.answer(error_text, reply_markup=kb)
        return
    
    # Если файл подходит - продолжаем без кнопки поддержки
    await state.update_data(
        receipt_file_id=message.document.file_id,
        receipt_file_name=file_name or "receipt.pdf"
    )
    
    text = (
        f"✅ Чек получен за {amount}⭐️!\n\n"
        "Теперь укажите получателя:\n"
        "- Напишите @username пользователя\n"
        "- Или напишите 'мне', если оформляете для себя"
    )
    
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"stars_upload_receipt_{amount}_{price}")],
        ]
    )
    
    await message.answer(text, reply_markup=kb)
    await state.set_state(StarsStates.waiting_recipient)

@router.message(StarsStates.waiting_receipt_pdf, ~F.document)
async def stars_handle_wrong_receipt_format(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != StarsStates.waiting_receipt_pdf:
        # Если состояние уже изменилось - игнорируем сообщение
        return

    data = await state.get_data()
    if not data or 'stars_amount' not in data or 'stars_price' not in data:
        await state.clear()
        await message.answer("❌ Сессия истекла. Начните процесс заново.")
        return

    amount = data['stars_amount']
    price = data['stars_price']

    # Проверяем, не является ли сообщение командой /cancel
    if message.text and message.text.strip() == '/cancel':
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_inline_kb())
        return

    error_text = (
        "❌ Неверный формат чека. Пожалуйста, отправляйте только файлы в формате PDF.\n"
        "Попробуйте ещё раз, но уже с форматом PDF.\n"
        "Если у вас возникнут вопросы, не стесняйтесь связаться со мной."
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📩 Связаться с поддержкой", url="https://t.me/Black_Prince01")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"stars_pay_sbp_{amount}_{price}")],
        ]
    )

    await message.answer(error_text, reply_markup=kb)
    # НЕ очищаем состояние, чтобы сообщение повторялось при каждой ошибке

# Обработчик кнопки "Назад" в состоянии ожидания PDF для Stars - удален, используется более функциональный обработчик ниже

@router.message(StarsStates.waiting_recipient)
async def stars_process_recipient(message: types.Message, state: FSMContext):
    # Получаем данные из состояния
    data = await state.get_data()
    recipient_raw = (message.text or '').strip().lower()

    if recipient_raw == "мне":
        recipient = f"@{message.from_user.username or message.from_user.id}"
    else:
        # Убираем @ если он есть в начале, затем добавляем обратно
        username = recipient_raw.lstrip('@')
        recipient = f"@{username}"
    
    # Получаем database ID пользователя
    user_profile = get_user_profile(message.from_user.id)
    if not user_profile:
        await message.answer("❌ Ошибка: пользователь не найден в базе данных.")
        await state.clear()
        return

    # Создаем заказ в базе данных
    order_id = create_order(
        user_id=user_profile['id'],  # Используем database ID
        order_type="stars",
        amount=data.get('stars_price', 0),
        status="pending",
        file_id=data.get('receipt_file_id'),
        extra_data={
            "amount": data.get('stars_amount', 0),
            "recipient": recipient
        }
    )

    # Формируем текст сообщения
    order_info = (
        f"✨ <b>НОВЫЙ ЗАКАЗ НА ЗВЁЗДЫ</b> ✨\n\n"
        f"👤 <b>Клиент:</b> @{message.from_user.username or message.from_user.id}\n"
        f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
        f"📩 <b>Получатель:</b> {recipient}\n"
        f"🔢 <b>Количество звёзд:</b> <b>{data.get('stars_amount', '?')} ⭐</b>\n"
        f"💰 <b>Сумма:</b> <b>{data.get('stars_price', '?')}₽</b>\n"
        f"⏱️ <b>Дата и время:</b> {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        f"📌 <b>Номер заказа:</b> <code>{order_id}</code>\n\n"
        f"#звёзды #{str(order_id).replace('-', '') if order_id else ''}"
    )

    # Создаем клавиатуру для админов
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"order_pay_{order_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"order_reject_{order_id}"),
        ],
        [
            InlineKeyboardButton(text="🗑 Удалить заказ", callback_data=f"order_delete_{order_id}")
        ]
    ])

    # Отправляем информацию админам
    try:
        for admin_id in ADMINS:
            try:
                if data.get('receipt_file_id'):
                    # Отправляем сообщение с прикрепленным чеком
                    admin_msg = await message.bot.send_document(
                        chat_id=admin_id,
                        document=data.get('receipt_file_id'),
                        caption=order_info,
                        reply_markup=admin_kb,
                        parse_mode="HTML"
                    )
                else:
                    # Если чека нет, отправляем просто текст
                    admin_msg = await message.bot.send_message(
                        chat_id=admin_id,
                        text=order_info,
                        reply_markup=admin_kb,
                        parse_mode="HTML"
                    )
                
                # Обновляем ID сообщения в базе данных (только для первого админа)
                if admin_id == ADMINS[0]:
                    update_order_status(order_id, admin_msg_id=admin_msg.message_id)
                
            except Exception as admin_error:
                logging.error(f"Ошибка отправки заказа админу {admin_id}: {admin_error}")
                continue

    except Exception as e:
        logging.error(f"Критическая ошибка при обработке заказа: {e}")
        await message.answer(
            "⚠️ Произошла ошибка при отправке заказа. Пожалуйста, попробуйте позже.",
            reply_markup=main_menu_inline_kb()
        )
        return

    # Отправляем подтверждение пользователю
    await message.answer(
        "✅ Ваш заказ на звёзды успешно отправлен на проверку!\n\n"
        "Администратор проверит ваш чек и отправит звёзды в ближайшее время.",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🛍️ Оставить отзыв", callback_data="leave_review")],
            [types.InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")],
        ])
    )
    
    # Очищаем состояние
    await state.clear()

# --- Кнопка "другая крипта" уже определена выше ---

def setup_routers(dp):
    dp.include_router(support.router)
    dp.include_router(admin_settings.router)
    dp.include_router(slot_machine.router)
    dp.include_router(activity_router)
    dp.include_router(debug.router)
    # ... другие роутеры ...

@router.callback_query(lambda c: c.data.startswith("withdraw_pay_"))
async def withdraw_pay(callback: types.CallbackQuery):
    try:
        parts = callback.data.split("_")
        withdrawal_id = int(parts[2])
        user_id = int(parts[3])
        amount = float(parts[4])
        final_amount = float(parts[5])
    except Exception:
        await callback.answer("Ошибка данных.")
        await callback.message.edit_text("✅ Заявка на вывод подтверждена.")
        return
    # Обновляем статус заявки
    from app.database.models import update_withdrawal_status, get_user_profile_by_id, unfreeze_balance
    update_withdrawal_status(withdrawal_id, 'done')
    # Получаем tg_id пользователя
    user_profile = get_user_profile_by_id(user_id)
    tg_id = user_profile['tg_id'] if user_profile else user_id
    # Размораживаем средства (они уже списаны при создании заявки)
    unfreeze_balance(tg_id, amount)
    # Оповещаем пользователя
    try:
        await callback.bot.send_message(tg_id, f"✅ Ваша заявка на вывод {amount:.2f}₽ выплачена. Спасибо за использование сервиса!")
    except Exception:
        pass
    await callback.answer("✅ Заявка на вывод подтверждена.")
    await callback.message.edit_text("✅ Заявка на вывод подтверждена.")

@router.callback_query(F.data == "admin_withdrawals")
async def admin_withdrawals_callback(callback: types.CallbackQuery):
    """Показывает список заявок на вывод средств с комиссией"""
    if callback.from_user.id not in ADMINS:
        await callback.answer("Нет доступа.")
        return
    
    withdrawals = get_all_pending_withdrawals()
    
    if not withdrawals:
        text = "📋 **Заявки на вывод средств** 📋\n\n❌ Нет активных заявок на вывод."
    else:
        text = "📋 **Заявки на вывод средств** 📋\n\n"
        
        for withdrawal in withdrawals[:10]:  # Показываем первые 10
            withdrawal_id, user_id, amount, status, created_at, requisites, type, extra = withdrawal
            
            # Получаем информацию о пользователе
            user_profile = get_user_profile_by_id(user_id)
            if not user_profile:
                continue
            
            tg_id, full_name, username = user_profile['tg_id'], user_profile['full_name'], user_profile['username']
            
            # Парсим extra данные для комиссии
            commission = 0
            final_amount = amount
            commission_percent = 3.0
            
            if extra:
                try:
                    extra_data = json.loads(extra)
                    commission = extra_data.get('commission', 0)
                    final_amount = extra_data.get('final_amount', amount)
                    commission_percent = extra_data.get('commission_percent', 3.0)
                except:
                    pass
            
            text += (
                f"🆔 **ID:** {withdrawal_id}\n"
                f"👤 **Пользователь:** {full_name} (@{username if username else 'без username'})\n"
                f"💳 **Сумма:** {amount}₽\n"
                f"💸 **Комиссия:** {commission:.2f}₽ ({commission_percent}%)\n"
                f"✅ **К выплате:** {final_amount:.2f}₽\n"
                f"📋 **Реквизиты:** {requisites[:50]}{'...' if len(requisites) > 50 else ''}\n"
                f"📅 **Дата:** {created_at}\n"
                f"🔗 **Действия:** [Подтвердить](withdraw_pay_{withdrawal_id}_{tg_id}_{amount}_{final_amount:.2f}) | [Отклонить](withdraw_reject_{withdrawal_id}_{tg_id}_{amount})\n\n"
            )
    
    try:
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_withdrawals")],
                [InlineKeyboardButton(text="🗑 Очистить все", callback_data="admin_clear_withdrawals")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
            ])
        )
    except Exception as e:
        await callback.answer("Ошибка: не удалось отредактировать сообщение.")
        print(f"Error in admin_withdrawals_callback: {e}")

@router.callback_query(F.data == "admin_clear_withdrawals")
async def admin_clear_withdrawals_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧹 Очистить заявки", callback_data="admin_clear_withdrawals_confirm")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")],
    ])
    await callback.message.answer("⚠️ Вы уверены, что хотите очистить все заявки на вывод и обнулить замороженные средства?", reply_markup=kb)

@router.callback_query(F.data == "admin_clear_withdrawals_confirm")
async def admin_clear_withdrawals_confirm_callback(callback: types.CallbackQuery):
    from app.database.models import clear_all_withdrawals_and_frozen
    clear_all_withdrawals_and_frozen()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")],
    ])
    await callback.message.edit_text("✅ Все заявки и замороженные средства очищены.", reply_markup=kb)

@router.callback_query(F.data.startswith("order_pay_"))
async def order_pay(callback: types.CallbackQuery):
    import datetime
    try:
        order_id = int(callback.data.split("_")[2])
        from app.database.models import get_order_by_id, update_order_status
        order = get_order_by_id(order_id)
        if not order:
            await callback.answer("❌ Заказ не найден")
            return

        confirm_time = datetime.datetime.now().strftime('%H:%M %d.%m.%Y')
        
        # Обновляем статус заказа
        update_order_status(
            order_id=order_id,
            status="completed",
            extra_data=json.dumps({
                **json.loads(order['extra_data'] if order['extra_data'] else {}),
                "confirmed_at": confirm_time,
                "confirmed_by": f"@{callback.from_user.username or callback.from_user.id}"
            })
        )

        # Получаем тип заказа
        order_type = order['order_type']

        # Обрабатываем реферальный бонус (только для платных заказов, не для вывода средств)
        if order_type != "withdraw":
            try:
                from app.utils.misc import process_referral_bonus
                await process_referral_bonus(callback.bot, order['user_id'], order['amount'], order_type, order_id)
            except Exception as e:
                logging.error(f"Ошибка обработки реферального бонуса: {e}")

        # Уведомляем пользователя
        try:
            # Получаем Telegram ID пользователя
            from app.database.models import get_user_profile_by_id
            user_profile = get_user_profile_by_id(order['user_id'])
            if user_profile:
                tg_id = user_profile['tg_id']
                message_text = ""

                if order_type == "premium":
                    message_text = f"✅ Ваш заказ Premium выполнен!\nВремя подтверждения: {confirm_time}"
                elif order_type == "stars":
                    message_text = f"✅ Ваши звёзды отправлены!\nВремя подтверждения: {confirm_time}"
                elif order_type == "crypto":
                    message_text = f"✅ Ваш заказ на криптовалюту выполнен!\nВремя подтверждения: {confirm_time}"
                elif order_type == "withdraw":
                    message_text = f"✅ Ваша заявка на вывод средств выполнена!\nВремя подтверждения: {confirm_time}"
                elif order_type == "activity_stars":
                    message_text = f"✅ Ваши звёзды за активность начислены!\nВремя подтверждения: {confirm_time}"
                elif order_type == "activity_ton":
                    message_text = f"✅ Ваши TON за активность начислены!\nВремя подтверждения: {confirm_time}"

                if message_text:
                    await callback.bot.send_message(tg_id, message_text)

        except Exception as e:
            logging.error(f"Ошибка уведомления пользователя: {e}")

        # Обновляем сообщение администратора
        try:
            new_text = (
                f"\n\n✅ ЗАКАЗ #{order_id} ВЫПОЛНЕН\n"
                f"Время подтверждения: {confirm_time}\n"
                f"Администратор: @{callback.from_user.username or callback.from_user.id}"
            )
            
            if callback.message.caption:
                await callback.message.edit_caption(
                    caption=callback.message.caption + new_text,
                    reply_markup=None  # Убираем кнопки после подтверждения
                )
            elif callback.message.text:
                await callback.message.edit_text(
                    text=callback.message.text + new_text,
                    reply_markup=None  # Убираем кнопки после подтверждения
                )
            else:
                await callback.message.answer(new_text)
                
        except Exception as e:
            logging.error(f"Ошибка обновления сообщения: {e}")

        await callback.answer("✅ Заказ выполнен!")
        
    except Exception as e:
        logging.error(f"Ошибка в order_pay: {e}")
        await callback.answer("❌ Ошибка подтверждения заказа")

@router.callback_query(F.data.startswith("order_reject_"))
async def order_reject(callback: types.CallbackQuery):
    import datetime
    try:
        order_id = int(callback.data.split("_")[2])
        from app.database.models import get_order_by_id, update_order_status
        order = get_order_by_id(order_id)
        if not order:
            await callback.answer("❌ Заказ не найден")
            return

        # Обновляем статус заказа
        update_order_status(
            order_id=order_id,
            status="rejected",
            extra_data=json.dumps({
                **json.loads(order['extra_data'] if order['extra_data'] else {}),
                "rejected_at": datetime.datetime.now().strftime('%H:%M %d.%m.%Y'),
                "rejected_by": f"@{callback.from_user.username or callback.from_user.id}"
            })
        )

        # Уведомляем пользователя
        try:
            # Получаем Telegram ID пользователя
            from app.database.models import get_user_profile_by_id
            user_profile = get_user_profile_by_id(order['user_id'])
            if user_profile:
                tg_id = user_profile['tg_id']
                order_type = order['order_type']
                reject_time = datetime.datetime.now().strftime('%H:%M %d.%m.%Y')

                # Если это заявка на вывод, возвращаем средства
                if order_type == "withdraw":
                    from app.database.models import unfreeze_balance
                    unfreeze_balance(tg_id, order['amount'])
                    message_text = f"❌ Ваша заявка на вывод {order['amount']:.2f}₽ отклонена.\nВремя отклонения: {reject_time}\nСредства возвращены на баланс."
                else:
                    message_text = f"❌ Ваш заказ отклонён.\nВремя отклонения: {reject_time}\nОбратитесь в поддержку для уточнения деталей."

                await callback.bot.send_message(tg_id, message_text, parse_mode="HTML")

        except Exception as e:
            logging.error(f"Ошибка уведомления пользователя: {e}")

        # Обновляем сообщение администратора
        try:
            reject_time = datetime.datetime.now().strftime('%H:%M %d.%m.%Y')
            new_text = (
                f"\n\n❌ ЗАКАЗ #{order_id} ОТКЛОНЁН\n"
                f"Время отклонения: {reject_time}\n"
                f"Администратор: @{callback.from_user.username or callback.from_user.id}"
            )

            if hasattr(callback.message, 'text'):
                await callback.message.edit_text(
                    f"{callback.message.text}{new_text}",
                    reply_markup=None,  # Убираем кнопки после отклонения
                    parse_mode="HTML"
                )
            else:
                await callback.message.answer(new_text, parse_mode="HTML")

        except Exception as e:
            logging.error(f"Ошибка обновления сообщения: {e}")

        await callback.answer("❌ Заказ отклонён")

    except Exception as e:
        logging.error(f"Ошибка в order_reject: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}")

@router.callback_query(F.data.startswith("order_delete_"))
async def order_delete(callback: types.CallbackQuery):
    try:
        order_id = int(callback.data.split("_")[2])
        # Удаляем заказ из базы
        from app.database.models import delete_order
        delete_order(order_id)
        
        await callback.answer("🗑 Заказ удалён")
        await callback.message.delete()
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}")

# Новый постраничный обработчик для заявок
@router.callback_query(lambda c: c.data.startswith("admin_orders"))
async def admin_orders_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    from app.database.models import get_all_orders, get_all_reviews
    import json
    
    orders = get_all_orders()
    reviews = get_all_reviews()
    
    if not orders and not reviews:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")],
        ])
        await callback.message.answer("📋 Нет активных заявок и отзывов.", reply_markup=kb)
        return
    
    text = "📋 <b>Все заявки и отзывы:</b>\n\n"
    
    # Заказы
    if orders:
        text += "🛍️ <b>ЗАКАЗЫ:</b>\n"
        type_icons = {"premium": "⭐️", "stars": "🌟", "crypto": "🦙", "withdraw": "💸"}
        for order in orders:
            order_id, user_id, order_type, amount, status, created_at, file_id, extra_data, admin_msg_id = order
            icon = type_icons.get(order_type, "❔")
            status_emoji = {"pending": "⏳", "completed": "✅", "rejected": "❌"}
            status_icon = status_emoji.get(status, "❔")
            
            text += f"{icon} <b>Заказ #{order_id}</b> {status_icon}\n"
            text += f"👤 ID: <code>{user_id}</code>\n"
            try:
                amount_f = float(amount)
                text += f"💰 Сумма: <b>{amount_f:.2f}₽</b>\n"
            except Exception:
                text += f"💰 Сумма: <b>{amount}₽</b>\n"
            text += f"📦 Тип: {order_type}\n"
            if extra_data:
                try:
                    extra = json.loads(extra_data)
                    if order_type == 'premium':
                        text += f"📅 Период: {extra.get('period','?')}\n"
                        text += f"🎁 Получатель: {extra.get('recipient','?')}\n"
                    elif order_type == 'stars':
                        text += f"⭐ Количество: {extra.get('amount','?')}\n"
                        text += f"🎁 Получатель: {extra.get('recipient','?')}\n"
                    elif order_type == 'crypto':
                        text += f"🦙 Монета: {extra.get('coin','?')}\n"
                        text += f"📊 Количество: {extra.get('amount','?')}\n"
                        text += f"🏦 Кошелёк: {extra.get('wallet','?')}\n"
                    elif order_type == 'withdraw':
                        text += f"💳 Реквизиты: {extra.get('requisites','?')}\n"
                except Exception:
                    pass
            text += f"⏰ Время: {created_at}\n\n"
    
    # Отзывы
    if reviews:
        text += "📝 <b>ОТЗЫВЫ:</b>\n"
        for review in reviews:
            review_id, user_id, content, status, created_at, file_id, admin_msg_id, channel_msg_id = review
            status_emoji = {"pending": "⏳", "published": "✅", "rejected": "❌"}
            status_icon = status_emoji.get(status, "❔")
            
            text += f"📝 <b>Отзыв #{review_id}</b> {status_icon}\n"
            text += f"👤 ID: <code>{user_id}</code>\n"
            text += f"📄 Статус: {status}\n"
            text += f"⏰ Время: {created_at}\n\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")],
    ])
    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "admin_clear_orders")
async def admin_clear_orders_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧹 Очистить заявки", callback_data="admin_clear_orders_confirm")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")],
    ])
    await callback.message.answer("⚠️ Вы уверены, что хотите очистить все заявки и отзывы?", reply_markup=kb)

@router.callback_query(F.data == "admin_clear_orders_confirm")
async def admin_clear_orders_confirm_callback(callback: types.CallbackQuery):
    from app.database.models import clear_all_orders, clear_all_reviews
    clear_all_orders()
    clear_all_reviews()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")],
    ])
    await callback.message.edit_text("✅ Все заявки и отзывы очищены.", reply_markup=kb)

# Универсальная функция рассылки сообщений всем администраторам
async def send_to_admins(bot, text, reply_markup=None, parse_mode=None, document=None, document_caption=None):
    admin_ids = ADMINS
    results = []
    for admin_id in admin_ids:
        try:
            if document:
                msg = await bot.send_document(admin_id, document, caption=document_caption, reply_markup=reply_markup)
            else:
                msg = await bot.send_message(admin_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
            results.append((admin_id, msg.message_id))
        except Exception as e:
            import logging
            logging.warning(f"Не удалось отправить сообщение админу {admin_id}: {e}")
    return results

# Дублирующийся обработчик удален - используется более функциональный обработчик ниже

@router.callback_query(lambda c: c.data.startswith('stars_pay_sbp_'), StarsStates.waiting_receipt_pdf)
async def back_from_stars_receipt_pdf(callback: types.CallbackQuery, state: FSMContext):
    # Извлекаем amount и price из callback_data
    parts = callback.data.replace("stars_pay_sbp_", "").split("_")
    amount, price = int(parts[0]), int(parts[1])

    await state.clear()
    await callback.message.delete()

    # Возвращаем в меню оплаты звезд с правильными параметрами
    text = (
        f"<b>Оплатите {price}₽ за {amount} звезд</b>\n"
        f"По номеру: <code>+79912148689</code>\n"
        f"Банк: <i>Альфа-Банк</i>\n\n"
        f"После оплаты загрузите чек"
    )

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🧾 Загрузить чек", callback_data=f"stars_upload_receipt_{amount}_{price}")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="stars")],
        ]
    )

    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

# Дублирующийся обработчик удален - используется обработчик выше (строка 783)

# Дублирующий обработчик crypto_confirm удален - используется основной обработчик

@router.message(Command("cancel"), 
        StateFilter(
        PremiumStates.waiting_receipt_pdf,
        StarsStates.waiting_receipt_pdf, 
        CryptoPayStates.waiting_receipt_pdf
    )
)
async def cancel_receipt_upload(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Загрузка чека отменена. Возвращаю в главное меню.",
        reply_markup=main_menu_inline_kb()
    )
    


async def check_subscription_required(user_id: int, bot) -> bool:
    from app.config_flags import proverka
    # Если проверка выключена - пропускаем
    if not proverka:
        return True
        
    # Если проверка включена - проверяем подписку
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status not in ['left', 'kicked']
    except Exception:
        return False

# В начало каждого хендлера (crypto_menu, stars_menu, tg_premium_menu) добавь:
# if not await check_subscription_required(call.from_user.id, call.bot):
#     await show_subscription_message(call, call.bot)
#     return

# Обработчик первой кнопки "Все заявки"
@router.callback_query(F.data == "admin_orders_0")
async def admin_orders_first(callback: types.CallbackQuery):
    # Удаляем старый обработчик, чтобы не было конфликтов
    pass

# Обработчик листания страниц заявок
@router.callback_query(F.data.startswith("admin_orders_page:"))
async def admin_orders_page_callback(callback: types.CallbackQuery):
    page = int(callback.data.split(":")[1])
    await callback.message.delete()
    await render_orders_page(callback, page)

async def render_orders_page(callback, page: int):
    from app.database.models import get_all_orders
    orders = get_all_orders()
    per_page = 5
    total_orders = len(orders)
    total_pages = (total_orders + per_page - 1) // per_page
    
    if page < 0 or page >= total_pages:
        await callback.bot.send_message(callback.from_user.id, f"❗️ Всего страниц: {total_pages}. Укажите число от 1 до {total_pages}.")
        return
        
    start = page * per_page
    end = start + per_page
    orders_page = orders[start:end]
    
    text = f"<b>ЗАЯВКИ (стр. {page + 1} из {total_pages}):</b>\n\n"
    status_emoji = {"pending": "⏳", "completed": "✅", "rejected": "❌"}
    type_icons = {"premium": "⭐️", "stars": "🌟", "crypto": "🦙", "withdraw": "💸", "slot_win": "🎰", "activity_reward": "🎁"}
    
    for order in orders_page:
        order_id, user_id, order_type, amount, status, created_at, file_id, extra_data, admin_msg_id = order
        icon = type_icons.get(order_type, "❔")
        stat = status_emoji.get(status, "❔")
        
        text += f"{icon} ЗАКАЗ #{order_id} {stat}\nID: {user_id}\n"
        
        try:
            amount_f = float(amount)
            text += f"💰 Сумма: {amount_f:.2f}₽\n"
        except Exception:
            text += f"💰 Сумма: {amount}\n"
            
        text += f"📊 Тип: {order_type}\n"
        
        try:
            extra = json.loads(order['extra_data']) if order['extra_data'] else {}
            
            # Добавляем отображение времени подтверждения для завершенных заказов
            if order['status'] == 'completed' and 'confirmed_at' in extra:
                text += f"🕒 Подтверждён: {extra['confirmed_at']}\n"
                
        except json.JSONDecodeError:
            pass
                
            # Остальные детали заказа...
            if order_type == 'premium':
                if 'period' in extra:
                    text += f"📅 Период: {extra.get('period','-')}\n"
                if 'recipient' in extra:
                    text += f"🎁 Получатель: {extra.get('recipient','-')}\n"
            elif order_type == 'stars':
                if 'amount' in extra:
                    text += f"⭐ Количество: {extra.get('amount','-')}\n"
                if 'recipient' in extra:
                    text += f"🎁 Получатель: {extra.get('recipient','-')}\n"
            elif order_type == 'crypto':
                if 'coin' in extra:
                    text += f"🦙 Монета: {extra.get('coin','-')}\n"
                if 'amount' in extra:
                    text += f"📊 Количество: {extra.get('amount','-')}\n"
                if 'wallet' in extra:
                    text += f"🏦 Кошелёк: {extra.get('wallet','-')}\n"
            elif order_type == 'withdraw':
                if 'requisites' in extra:
                    text += f"💳 Реквизиты: {extra.get('requisites','-')}\n"
                    
        except Exception as e:
            logging.warning(f"[render_orders_page] extra_data parse error: {e}")
            
        text += f"⏰ Создан: {created_at}\n\n"
        
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_orders_page:{page-1}"))
    if (page + 1) < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Вперёд", callback_data=f"admin_orders_page:{page+1}"))
    nav_buttons.append(InlineKeyboardButton(text="🏠 В меню", callback_data="admin_panel"))
    
    kb = InlineKeyboardMarkup(inline_keyboard=[nav_buttons])
    await callback.bot.send_message(callback.from_user.id, text, parse_mode="HTML", reply_markup=kb)

@router.message(Command("clear_calendar"))
async def clear_calendar_command(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.answer("Нет доступа.")
        return
    from app.database.models import clear_all_calendar_data
    clear_all_calendar_data()
    await message.answer("✅ Вся активность календаря очищена у всех пользователей. Теперь все как новые!")

@router.callback_query(F.data == "check_subscription_2")
async def check_subscription_handler_2(callback: types.CallbackQuery):
    """Обработчик для проверки подписки - возвращает в главное меню"""
    await main_menu_handler(callback)

# ===== ФУНКЦИИ БЕЗ УДАЛЕНИЯ СООБЩЕНИЙ (ДЛЯ РАССЫЛКИ) =====

async def stars_menu_no_delete(call: types.CallbackQuery):
    """Меню звезд БЕЗ удаления предыдущего сообщения"""
    # Проверяем черный список
    if await check_blacklist_and_respond(call.from_user.id, call):
        return

    # Используем единую функцию проверки подписки
    if not await check_subscription_required(call.from_user.id, call.bot):
        await show_subscription_message(call, call.bot)
        return

    stars_photo = get_admin_setting('stars_photo', 'https://imgur.com/a/0Tx7psa.jpeg')
    stars_description = get_admin_setting('stars_description', '''
🌟 Добро пожаловать в раздел покупки звёзд!

Здесь вы можете выбрать звёзды для разных случаев: подарок, награда или просто для себя.

✨ Как это работает?
1️⃣ Выберите количество звёзд
2️⃣ Оплатите любым удобным способом

🔒 Гарантируем безопасность и легальность сделок.
''')
    if not stars_description:
        stars_description = '''
🌟 Добро пожаловать в раздел покупки звёзд!

Здесь вы можете выбрать звёзды для разных случаев: подарок, награда или просто для себя.

✨ Как это работает?
1️⃣ Выберите количество звёзд
2️⃣ Оплатите любым удобным способом

🔒 Гарантируем безопасность и легальность сделок.
'''
    kb = stars_menu_inline_kb()
    await call.message.answer_photo(
        photo=stars_photo,
        caption=stars_description,
        reply_markup=kb,
        parse_mode="HTML"
    )

async def reviews_menu_no_delete(call: types.CallbackQuery, bot: Bot):
    """Меню отзывов БЕЗ удаления предыдущего сообщения"""
    # Проверяем черный список
    if await check_blacklist_and_respond(call.from_user.id, call):
        return

    if not await check_subscription(call.from_user.id, bot):
        await show_subscription_message(call, bot)
        return

    try:
        reviews_photo = "https://imgur.com/a/5cDMyX0.jpeg"
        reviews_text = (
    "🌟 Отзывы наших клиентов 🌟\n\n"
    "Мы ценим ваше мнение и стремимся сделать наш сервис лучше с каждым днем! "
    "Здесь вы можете ознакомиться с отзывами наших клиентов, которые уже приобрели звёзды через LegalStars. "
    "Ваши впечатления важны для нас!\n\n"
    "💬 Оставьте свой отзыв!\n\n"
    "Ваш опыт может помочь другим пользователям сделать правильный выбор. "
    "Поделитесь своими впечатлениями о покупке звёзд, качестве обслуживания "
    "и общем опыте взаимодействия с нашим ботом."
)

        try:
            await call.message.answer_photo(
                photo=reviews_photo,
                caption=reviews_text,
                reply_markup=reviews_menu_inline_kb(),
                parse_mode="HTML"
            )
        except Exception as e:
            await call.message.answer(
                reviews_text,
                reply_markup=reviews_menu_inline_kb(),
                parse_mode="HTML"
            )

        await call.answer()
    except Exception as e:
        logging.error(f"Ошибка в reviews_menu_no_delete: {e}")
        await call.answer("⚠️ Произошла ошибка")

async def tg_premium_menu_no_delete(call: types.CallbackQuery):
    """Меню Telegram Premium БЕЗ удаления предыдущего сообщения"""
    # Проверяем черный список
    if await check_blacklist_and_respond(call.from_user.id, call):
        return

    # Проверка подписки (только если включена в настройках)
    from app.config_flags import proverka
    if proverka and not await check_subscription(call.from_user.id, call.bot):
        await show_subscription_message(call, call.bot)
        return

    premium_photo = get_admin_setting('premium_photo', 'https://imgur.com/a/VJU8JNk.jpeg')
    premium_description = get_admin_setting('premium_description', '💎 Telegram Premium — это официальная подписка от Telegram, дающая дополнительные возможности. Выберите желаемый срок подписки:')
    kb = premium_menu_inline_kb()
    await call.message.answer_photo(
        photo=premium_photo,
        caption=premium_description,
        reply_markup=kb
    )

async def crypto_menu_no_delete(call: types.CallbackQuery):
    """Меню криптовалют БЕЗ удаления предыдущего сообщения"""
    # Проверяем черный список
    if await check_blacklist_and_respond(call.from_user.id, call):
        return

    # Проверка подписки (только если включена в настройках)
    from app.config_flags import proverka
    if proverka and not await check_subscription(call.from_user.id, call.bot):
        await show_subscription_message(call, call.bot)
        return

    crypto_photo = get_admin_setting('crypto_photo', 'https://imgur.com/a/3ZZOHNJ.jpeg')
    crypto_description = get_admin_setting('crypto_description', 'Теперь у нас вы можете приобрести криптовалюту за рубли!\n\nЛегко, быстро и безопасно — просто выберите нужный раздел, а всё остальное сделаем мы за вас.\n\n🔐 Ваша безопасность и конфиденциальность гарантированы.');
    kb = crypto_menu_inline_kb()
    await call.message.answer_photo(
        photo=crypto_photo,
        caption=crypto_description,
        reply_markup=kb
    )

async def activity_menu_from_main_no_delete(call: types.CallbackQuery, bot: Bot):
    """Меню активности БЕЗ удаления предыдущего сообщения"""
    if not await check_subscription(call.from_user.id, bot):
        await show_subscription_message(call, bot)
        return

    try:
        user_id = call.from_user.id
        current_date = datetime.datetime.now().date()

        # Получаем серию из БД
        from app.database.models import get_user_activity_streak
        streak = get_user_activity_streak(user_id)

        text = (
            "<b>📅 Календарь активности</b>\n\n"
            "Календарь активности — это когда пользователь заходит в бота и отмечает свою активность за текущий день.\n"
            "Если пользователь заходит подряд несколько дней (например, 7, 14 или 20 дней), он получает награду или бонус.\n"
            "Если пользователь пропускает хотя бы один день, его \"цепочка\" активности сбрасывается — счетчик возвращается к нулю.\n"
            "Например: пользователь зашел 20 дней подряд, а на 21-й день не зашел — его прогресс сбрасывается до нуля.\n\n"
            f"<b>🔥 Ваша текущая серия:</b> {streak} дней\n"
            f"📌 <b>Сегодня:</b> {current_date.strftime('%d.%m.%Y')}"
        )

        await call.message.answer(
            text,
            reply_markup=activity_calendar_kb(),
            parse_mode="HTML"
        )

    except Exception as e:
        logging.error(f"Ошибка в activity_menu_no_delete: {str(e)}")
        await call.answer("⚠️ Произошла ошибка", show_alert=True)

async def profile_menu_no_delete(call: types.CallbackQuery, bot: Bot, state: FSMContext):
    """Меню профиля БЕЗ удаления предыдущего сообщения"""
    # Проверяем черный список
    if await check_blacklist_and_respond(call.from_user.id, call):
        return

    # Проверяем подписку (если требуется)
    if not await check_subscription(call.from_user.id, bot):
        await show_subscription_message(call, bot)
        return

    try:
        # Получаем данные пользователя
        user = get_user_profile(call.from_user.id)
        if not user:
            await call.message.answer(
                "Профиль не найден.",
                reply_markup=main_menu_inline_kb()
            )
            return

        # Форматируем данные
        balance = float(user['balance'] or 0)
        frozen = float(user['frozen'] or 0)
        reg_date = user['reg_date'] or "не указана"

        # Получаем настройки профиля из админ панели
        profile_description = get_admin_setting('profile_description', '🚀 <b>Ваш профиль</b>\n\nЗдесь вы можете посмотреть информацию о своем аккаунте, балансе и истории операций.')
        profile_photo = get_admin_setting('profile_photo', 'https://imgur.com/a/TkOPe7c.jpeg')

        # Формируем текст
        text = (
            f"{profile_description}\n\n"
            f"🆔 <b>ID:</b> <a href='tg://user?id={user['tg_id']}'>{user['tg_id']}</a>\n"
            f"📅 <b>Регистрация:</b> {reg_date}\n"
            f"💰 <b>Баланс:</b> {balance:.2f}₽\n"
            f"❄️ <b>Заморожено:</b> {frozen:.2f}₽\n"
        )

        # Добавляем реферальную информацию, если включено
        if ref_active:
            from app.database.models import get_unclaimed_referrals_count

            referrals = get_referrals_count(user['tg_id'])
            bot_username = (await bot.me()).username
            ref_link = f"https://t.me/{bot_username}?start=ref_{user['tg_id']}"

            # Получаем количество неактивированных рефералов
            try:
                unclaimed_count = await get_unclaimed_referrals_count(user['id'])
            except Exception as e:
                logging.error(f"Ошибка получения неактивированных рефералов: {e}")
                unclaimed_count = 0

            text += (
                f"\n👥 <b>Приглашено:</b> {referrals} пользователей\n"
                f"🎁 <b>Неактивированных:</b> {unclaimed_count} рефералов\n"
                f"🔗 <b>Реферальная ссылка:</b>\n<code>{ref_link}</code>\n"
            )

            if unclaimed_count > 0:
                text += f"\n💡 У вас есть {unclaimed_count} неактивированных рефералов! Активируйте их в слот-машине для получения бонусных попыток.\n"

        # Создаем клавиатуру
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📤 Вывести средства",
                        callback_data="withdraw"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="main_menu"
                    )
                ]
            ]
        )

        # НЕ удаляем предыдущее сообщение, просто отправляем новое
        await call.message.answer_photo(
            photo=profile_photo,
            caption=text,
            reply_markup=kb,
            parse_mode="HTML"
        )

    except Exception as e:
        logging.error(f"Ошибка в profile_menu_no_delete {call.from_user.id}: {e}")
        await call.message.answer(
            "⚠️ Произошла ошибка при загрузке профиля. Попробуйте позже.",
            reply_markup=main_menu_inline_kb()
        )

def get_main_greeting(user):
    user_name = user.full_name or user.username or f"ID: {user.id}" if user else "Пользователь"
    return f"<b>{user_name}</b>, Добро Пожаловать в Legal Stars!✨"