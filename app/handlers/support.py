"""
Обработчики системы технической поддержки
"""
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Bot, types
import logging
import asyncio
from datetime import datetime
from typing import Optional

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import html

from app.database.models import get_user_roulette_attempts
from app.config import ADMINS, SUPPORT_CHAT_ID
from app.database.models import (
    create_support_ticket,
    get_support_ticket_by_id,
    update_support_ticket_status,
    get_user_profile_by_id,
    get_user_profile,
    get_or_create_user,
    get_admin_setting,
    get_all_support_tickets,
    delete_support_ticket,
    clear_all_support_tickets
)
from app.keyboards.main import support_menu_kb, admin_support_tickets_kb, admin_support_ticket_actions_kb, admin_clear_all_tickets_kb
from app.utils.misc import is_admin

# Импортируем константы каналов
from app.constants import CHANNEL_ID, CHANNEL_USERNAME, CHANNEL_LINK

router = Router()
logger = logging.getLogger(__name__)

class SupportStates(StatesGroup):
    """Состояния для системы поддержки"""
    waiting_for_message = State()
    waiting_for_admin_reply = State()

# Словарь для хранения активных сессий админов
admin_sessions = {}

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

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
        
@router.callback_query(F.data == "support")
async def support_menu(callback: types.CallbackQuery, bot: Bot):
    """
    Меню поддержки с фото и редактируемым текстом
    """

    # Проверка черного списка
    from app.handlers.user import check_blacklist_and_respond
    if await check_blacklist_and_respond(callback.from_user.id, callback):
        return

    # Проверка подписки (только если включена в настройках)
    from app.config_flags import proverka
    if proverka and not await check_subscription(callback.from_user.id, bot):
        await show_subscription_message(callback, bot)
        return

    try:
        support_photo = get_admin_setting('support_photo', 'https://imgur.com/a/taqnUZN.jpeg')
        support_description = get_admin_setting(
    'support_description',
    'Поддержка Legal Stars 🎨\n\n'
    '🌟 Мы здесь, чтобы помочь вам! 🌟\n\n'
    'Если у вас возникли вопросы или проблемы, наша команда поддержки всегда готова прийти на помощь. '
    'Мы ценим каждого клиента и стремимся сделать ваше взаимодействие с нами максимально комфортным.\n\n'
    'Как связаться с нами?\n'
    '📩 Напишите нам в личные сообщения, воспользовавшись кнопкой ниже. Мы ответим вам в кратчайшие сроки!'
)

        msg = getattr(callback, 'message', None)
        
        # Пытаемся отправить фото с описанием
        try:
            if msg and hasattr(msg, 'edit_media'):
                # Если можно редактировать существующее медиа
                media = types.InputMediaPhoto(
                    media=support_photo,
                    caption=support_description,
                    parse_mode="HTML"
                )
                await msg.edit_media(
                    media=media,
                    reply_markup=support_menu_kb()
                )
            elif msg and hasattr(msg, 'answer_photo'):
                await msg.answer_photo(
                    photo=support_photo,
                    caption=support_description,
                    parse_mode="HTML",
                    reply_markup=support_menu_kb()
                )
            else:
                # Fallback: отправляем просто текст
                await (msg or callback.message).answer(
                    support_description,
                    parse_mode="HTML",
                    reply_markup=support_menu_kb()
                )
        except Exception as media_error:
            logging.warning(f"Не удалось отправить фото поддержки: {media_error}")
            await (msg or callback.message).answer(
                support_description,
                parse_mode="HTML",
                reply_markup=support_menu_kb()
            )

        await callback.answer()

    except Exception as e:
        logging.error(f"[SUPPORT] Ошибка в support_menu: {e}", exc_info=True)
        try:
            await callback.answer("❌ Ошибка. Попробуйте позже.", show_alert=True)
        except:
            pass  # Если даже ответить не удалось
            
        # Уведомление админам
        await notify_admins(
            bot,
            f"Ошибка в меню поддержки у @{callback.from_user.username or callback.from_user.id}:\n{str(e)}"
        )

async def support_menu_no_delete(callback: types.CallbackQuery, bot: Bot):
    """
    Меню поддержки БЕЗ удаления предыдущего сообщения (для рассылки)
    """

    # Проверка черного списка
    from app.handlers.user import check_blacklist_and_respond
    if await check_blacklist_and_respond(callback.from_user.id, callback):
        return

    # Проверка подписки (только если включена в настройках)
    from app.config_flags import proverka
    if proverka and not await check_subscription(callback.from_user.id, bot):
        await show_subscription_message(callback, bot)
        return

    try:
        support_photo = get_admin_setting('support_photo', 'https://imgur.com/a/taqnUZN.jpeg')
        support_description = get_admin_setting(
    'support_description',
    'Поддержка Legal Stars 🎨\n\n'
    '🌟 Мы здесь, чтобы помочь вам! 🌟\n\n'
    'Если у вас возникли вопросы или проблемы, наша команда поддержки всегда готова прийти на помощь. '
    'Мы ценим каждого клиента и стремимся сделать ваше взаимодействие с нами максимально комфортным.\n\n'
    'Как связаться с нами?\n'
    '📩 Напишите нам в личные сообщения, воспользовавшись кнопкой ниже. Мы ответим вам в кратчайшие сроки!'
)

        # НЕ удаляем предыдущее сообщение, просто отправляем новое
        try:
            await callback.message.answer_photo(
                photo=support_photo,
                caption=support_description,
                parse_mode="HTML",
                reply_markup=support_menu_kb()
            )
        except Exception as media_error:
            logging.warning(f"Не удалось отправить фото поддержки: {media_error}")
            await callback.message.answer(
                support_description,
                parse_mode="HTML",
                reply_markup=support_menu_kb()
            )

        await callback.answer()

    except Exception as e:
        logging.error(f"[SUPPORT] Ошибка в support_menu_no_delete: {e}", exc_info=True)
        try:
            await callback.answer("❌ Ошибка. Попробуйте позже.", show_alert=True)
        except:
            pass  # Если даже ответить не удалось

        # Уведомление админам
        await notify_admins(
            bot,
            f"Ошибка в меню поддержки (no_delete) у @{callback.from_user.username or callback.from_user.id}:\n{str(e)}"
        )

@router.callback_query(F.data == "support_contact")
async def support_contact(callback: types.CallbackQuery, state: FSMContext):
    """Создание тикета поддержки"""
    try:
        text = (
            "✍️ <b>Создание тикета поддержки</b>\n\n"
            "Опишите вашу проблему или вопрос. Мы постараемся ответить как можно скорее.\n\n"
            "Для отмены отправьте /cancel"
        )
        
        if callback.message and hasattr(callback.message, 'answer'):
            await callback.message.answer(
                text,
                parse_mode="HTML"
            )
        
        await state.set_state(SupportStates.waiting_for_message)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"[SUPPORT] Ошибка в support_contact: {e}")
        await callback.answer("❌ Ошибка. Попробуйте позже.", show_alert=True)

@router.message(SupportStates.waiting_for_message)
async def process_support_message(message: types.Message, state: FSMContext):
    """Обработка сообщения пользователя для создания тикета"""
    try:
        # Проверяем, что это не команда и есть текст
        if not message.text or message.text.startswith('/'):
            # Если это не текст, а файл/фото/документ — отправляем ошибку
            if message.document or message.photo or message.sticker or message.video or message.audio or message.voice:
                await message.answer("Пожалуйста, отправьте текстовое сообщение для поддержки.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]]))
                return
            return
        
        # Проверяем, что это не админ
        if message.from_user and is_admin(message.from_user.id):
            await message.answer("❌ Администраторы не могут создавать тикеты поддержки.")
            await state.clear()
            return
        
        user = message.from_user
        if not user:
            return
        
        # Получаем или создаем профиль пользователя
        user_profile = get_user_profile(user.id)
        if not user_profile:
            get_or_create_user(
                user.id, 
                user.full_name or user.username or str(user.id),
                user.username or "",
                datetime.now().strftime("%Y-%m-%d")
            )
            user_profile = get_user_profile(user.id)
        
        if not user_profile:
            await message.answer("❌ Ошибка создания профиля. Попробуйте позже.")
            await state.clear()
            return
        
        # Создаем тикет
        ticket_id = create_support_ticket(
            user_profile['id'],  # db_user_id
            user.username or "",
            user.full_name or user.username or str(user.id),
            message.text
        )
        
        # Подтверждение пользователю
        await message.answer(
            f"✅ <b>Тикет #{ticket_id} создан!</b>\n\n"
            f"📝 <b>Ваше сообщение:</b>\n{html.escape(message.text)}\n\n"
            f"Мы рассмотрим ваш запрос и ответим в ближайшее время.",
            parse_mode="HTML"
        )
        
        # Отправляем тикет в чат поддержки
        user_display = f"@{user.username}" if user.username else (user.full_name or f"ID: {user.id}")
        support_text = (
            f"📩 <b>Новое обращение в техподдержку</b>\n\n"
            f"👤 <b>Пользователь:</b> {html.escape(user_display)}\n"
            f"🆔 <b>Telegram ID:</b> <code>{user.id}</code>\n"
            f"📝 <b>Сообщение:</b>\n{html.escape(message.text)}"
        )
        
        # Получаем имя бота для создания правильной ссылки
        try:
            bot_info = await message.bot.me()
            bot_username = bot_info.username
            reply_url = f"https://t.me/{bot_username}?start=reply_{ticket_id}"
        except Exception:
            # Fallback на callback если не удалось получить имя бота
            reply_url = None

        if reply_url:
            reply_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Ответить", url=reply_url)],
                [InlineKeyboardButton(text="✅ Закрыть", callback_data=f"close_ticket_{ticket_id}")]
            ])
        else:
            reply_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Ответить", callback_data=f"reply_ticket_{ticket_id}")],
                [InlineKeyboardButton(text="✅ Закрыть", callback_data=f"close_ticket_{ticket_id}")]
            ])
        
        try:
            if message.bot and SUPPORT_CHAT_ID:
                logger.info(f"[SUPPORT] Отправляем тикет #{ticket_id} в чат поддержки {SUPPORT_CHAT_ID}")
                await message.bot.send_message(
                    int(SUPPORT_CHAT_ID),
                    support_text,
                    parse_mode="HTML",
                    reply_markup=reply_kb
                )
                logger.info(f"[SUPPORT] Тикет #{ticket_id} успешно отправлен в чат поддержки")
            elif not SUPPORT_CHAT_ID:
                logger.warning("[SUPPORT] SUPPORT_CHAT_ID не настроен - уведомления в чат поддержки отключены")
        except Exception as e:
            logger.error(f"[SUPPORT] Ошибка отправки в чат поддержки {SUPPORT_CHAT_ID}: {e}")
            await message.answer("⚠️ Тикет создан, но возникла проблема с отправкой в чат поддержки.")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"[SUPPORT] Ошибка в process_support_message: {e}")
        await message.answer("❌ Ошибка создания тикета. Попробуйте позже.")
        await state.clear()

@router.callback_query(F.data.startswith("reply_ticket_"))
async def reply_ticket_handler(callback: types.CallbackQuery):
    """Обработчик кнопки 'Ответить' на тикет"""
    try:
        if not callback.from_user or not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        if not callback.data:
            await callback.answer("❌ Ошибка данных", show_alert=True)
            return
        
        ticket_id = int(callback.data.replace("reply_ticket_", ""))
        ticket = get_support_ticket_by_id(ticket_id)
        
        if not ticket:
            await callback.answer("❌ Тикет не найден", show_alert=True)
            return
        
        # Сохраняем сессию админа
        admin_sessions[callback.from_user.id] = {
            'ticket_id': ticket_id,
            'user_id': ticket['user_id'],
            'username': ticket['username'],
            'full_name': ticket['full_name'],
            'message': ticket['message']
        }
        
        # Получаем профиль пользователя для получения Telegram ID
        user_profile = get_user_profile_by_id(ticket['user_id'])
        user_display = f"@{ticket['username']}" if ticket['username'] else ticket['full_name']
        user_tg_id = user_profile['tg_id'] if user_profile else "неизвестен"

        # Отправляем сообщение админу в ЛС
        admin_text = (
            f"✍️ <b>Ответ на тикет #{ticket_id}</b>\n\n"
            f"👤 <b>Пользователь:</b> {html.escape(user_display)}\n"
            f"🆔 <b>Telegram ID:</b> <code>{user_tg_id}</code>\n"
            f"📝 <b>Сообщение:</b>\n{html.escape(ticket['message'])}\n\n"
            f"💬 <b>Введите ваш ответ:</b>"
        )
        
        try:
            if callback.bot:
                await callback.bot.send_message(
                    callback.from_user.id,
                    admin_text,
                    parse_mode="HTML"
                )
                await callback.answer("✅ Ожидаю ваш ответ в ЛС!", show_alert=True)
        except Exception as e:
            logger.error(f"[SUPPORT] Ошибка отправки сообщения админу: {e}")
            await callback.answer("❌ Ошибка. Проверьте, что бот может писать вам в ЛС.", show_alert=True)
            
    except Exception as e:
        logger.error(f"[SUPPORT] Ошибка в reply_ticket_handler: {e}")
        await callback.answer("❌ Ошибка при подготовке ответа", show_alert=True)

@router.callback_query(F.data.startswith("close_ticket_"))
async def close_ticket_handler(callback: types.CallbackQuery):
    """Обработчик кнопки 'Закрыть' тикет"""
    try:
        if not callback.from_user or not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        if not callback.data:
            await callback.answer("❌ Ошибка данных", show_alert=True)
            return
        ticket_id = int(callback.data.replace("close_ticket_", ""))
        ticket = get_support_ticket_by_id(ticket_id)
        if not ticket:
            await callback.answer("❌ Тикет не найден", show_alert=True)
            return
        # Обновляем статус тикета
        update_support_ticket_status(ticket_id, "closed")
        # Уведомляем пользователя
        user_profile = get_user_profile_by_id(ticket['user_id'])
        if user_profile and callback.bot:
            try:
                await callback.bot.send_message(
                    user_profile['tg_id'],  # tg_id
                    f"✅ <b>Тикет #{ticket_id} закрыт</b>\n\n"
                    f"Ваш тикет был закрыт администратором без ответа.",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"[SUPPORT] Ошибка отправки уведомления о закрытии: {e}")
        # Вместо edit_text отправляем новое сообщение в чат поддержки
        msg = callback.message
        if msg and hasattr(msg, 'answer'):
            await msg.answer(
                f"✅ <b>Тикет #{ticket_id} закрыт</b>",
                parse_mode="HTML"
            )
        await callback.answer("✅ Тикет закрыт", show_alert=True)
    except Exception as e:
        logger.error(f"[SUPPORT] Ошибка в close_ticket_handler: {e}")
        await callback.answer("❌ Ошибка при закрытии тикета", show_alert=True)

@router.message(F.chat.type == 'private')
async def handle_admin_reply(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        # Если пользователь в FSM-сценарии — не обрабатывать это сообщение здесь
        return
    # Не реагировать на команды
    if message.text and message.text.startswith('/'):
        return
    try:
        # Строгая проверка: только админы с активными сессиями
        if not message.from_user or not is_admin(message.from_user.id):
            return

        admin_id = message.from_user.id

        # ВАЖНО: Проверяем, есть ли активная сессия - если нет, то НЕ обрабатываем
        if admin_id not in admin_sessions:
            # Если нет активной сессии поддержки, просто игнорируем сообщение
            # Это позволит другим обработчикам (например, admin_settings) обработать сообщение
            return
        
        session = admin_sessions[admin_id]
        ticket_id = session['ticket_id']
        
        # Проверяем, что тикет еще существует
        ticket = get_support_ticket_by_id(ticket_id)
        if not ticket:
            await message.answer("❌ Тикет не найден или был удален.")
            del admin_sessions[admin_id]
            return
        
        # Получаем профиль пользователя
        user_profile = get_user_profile_by_id(session['user_id'])
        if not user_profile:
            await message.answer("❌ Профиль пользователя не найден.")
            del admin_sessions[admin_id]
            return

        # Отправляем ответ пользователю
        try:
            if message.bot and message.text:
                # Убеждаемся, что tg_id это число
                tg_id = int(user_profile['tg_id'])
                await message.bot.send_message(
                    tg_id,
                    f"💬 <b>Ответ от поддержки на тикет #{ticket_id}</b>\n\n"
                    f"{html.escape(message.text)}",
                    parse_mode="HTML"
                )
                
                # Обновляем статус тикета
                update_support_ticket_status(
                    ticket_id, 
                    "replied", 
                    message.text,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                
                # Уведомляем админа
                await message.answer("✅ Ответ отправлен пользователю")
                
                # Удаляем сессию
                del admin_sessions[admin_id]
                
        except Exception as e:
            logger.error(f"[SUPPORT] Ошибка отправки ответа пользователю: {e}")
            await message.answer("❌ Ошибка отправки ответа. Пользователь мог заблокировать бота.")
            del admin_sessions[admin_id]
            
    except Exception as e:
        logger.error(f"[SUPPORT] Ошибка в handle_admin_reply: {e}")
        # Не показываем ошибку пользователю, так как это может быть обычный пользователь в FSM состоянии

@router.message(Command("cancel"))
async def cancel_support(message: types.Message, state: FSMContext):
    """Отмена создания тикета"""
    try:
        await state.clear()
        await message.answer("❌ Создание тикета отменено.")
    except Exception as e:
        logger.error(f"[SUPPORT] Ошибка в cancel_support: {e}")

@router.message(Command("reply"))
async def admin_reply_command(message: types.Message):
    """Команда для ответа на тикет: /reply <ticket_id> <текст ответа>"""
    try:
        if not message.from_user or not is_admin(message.from_user.id):
            return
        
        if not message.text or not message.text.startswith('/reply '):
            return
        
        # Парсим команду
        parts = message.text.split(' ', 2)
        if len(parts) < 3:
            await message.answer("❌ Использование: /reply <ticket_id> <текст ответа>")
            return
        
        try:
            ticket_id = int(parts[1])
        except ValueError:
            await message.answer("❌ Неверный ID тикета")
            return
        
        reply_text = parts[2]
        
        # Получаем тикет
        ticket = get_support_ticket_by_id(ticket_id)
        if not ticket:
            await message.answer("❌ Тикет не найден")
            return
        
        # Получаем профиль пользователя
        user_profile = get_user_profile_by_id(ticket['user_id'])
        if not user_profile:
            await message.answer("❌ Профиль пользователя не найден")
            return
        
        # Отправляем ответ
        try:
            if message.bot:
                await message.bot.send_message(
                    user_profile['tg_id'],  # tg_id
                    f"💬 <b>Ответ от поддержки на тикет #{ticket_id}</b>\n\n"
                    f"{html.escape(reply_text)}",
                    parse_mode="HTML"
                )
                
                # Обновляем статус тикета
                update_support_ticket_status(
                    ticket_id, 
                    "replied", 
                    reply_text,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                
                await message.answer("✅ Ответ отправлен пользователю")
                
        except Exception as e:
            logger.error(f"[SUPPORT] Ошибка отправки ответа через команду: {e}")
            await message.answer("❌ Ошибка отправки ответа. Пользователь мог заблокировать бота.")
            
    except Exception as e:
        logger.error(f"[SUPPORT] Ошибка в admin_reply_command: {e}")
        await message.answer("❌ Ошибка обработки команды")

@router.message(F.reply_to_message)
async def support_reply_in_group(message: types.Message):
    """Ответ на тикет через reply в группе поддержки"""
    try:
        if not message.from_user or not is_admin(message.from_user.id):
            return
        
        if not SUPPORT_CHAT_ID or message.chat.id != int(SUPPORT_CHAT_ID):
            return
        
        # Проверяем, что это ответ на сообщение бота с тикетом
        if not message.reply_to_message or not message.reply_to_message.from_user or not message.reply_to_message.from_user.is_bot:
            return
        
        # Ищем ticket_id в тексте сообщения
        reply_text = message.reply_to_message.text or ""
        if "Новое обращение в техподдержку" not in reply_text:
            return
        
        # Извлекаем ticket_id из текста (ищем #номер)
        import re
        match = re.search(r'#(\d+)', reply_text)
        if not match:
            await message.answer("❌ Не удалось определить ID тикета")
            return
        
        ticket_id = int(match.group(1))
        
        # Получаем тикет
        ticket = get_support_ticket_by_id(ticket_id)
        if not ticket:
            await message.answer("❌ Тикет не найден")
            return
        
        # Получаем профиль пользователя
        user_profile = get_user_profile_by_id(ticket['user_id'])
        if not user_profile:
            await message.answer("❌ Профиль пользователя не найден")
            return
        
        # Отправляем ответ пользователю
        try:
            if message.bot and message.text:
                await message.bot.send_message(
                    user_profile['tg_id'],  # tg_id
                    f"💬 <b>Ответ от поддержки на тикет #{ticket_id}</b>\n\n"
                    f"{html.escape(message.text)}",
                    parse_mode="HTML"
                )
                
                # Обновляем статус тикета
                update_support_ticket_status(
                    ticket_id, 
                    "replied", 
                    message.text,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                
                await message.answer("✅ Ответ отправлен пользователю")
                
        except Exception as e:
            logger.error(f"[SUPPORT] Ошибка отправки ответа через reply: {e}")
            await message.answer("❌ Ошибка отправки ответа. Пользователь мог заблокировать бота.")
            
    except Exception as e:
        logger.error(f"[SUPPORT] Ошибка в support_reply_in_group: {e}")
        # Не показываем ошибку, так как это функция для группы поддержки

@router.callback_query(F.data == "admin_support_tickets")
async def admin_support_tickets(callback: types.CallbackQuery):
    """Показать все тикеты поддержки для админа"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    tickets = get_all_support_tickets()
    if not tickets:
        if callback.message and hasattr(callback.message, 'answer'):
            await callback.message.answer("Нет тикетов поддержки.", reply_markup=admin_support_tickets_kb([]))
        await callback.answer()
        return
    if callback.message and hasattr(callback.message, 'answer'):
        await callback.message.answer(
            "🎟️ <b>Все тикеты поддержки</b>\n\nВыберите тикет для просмотра или удаления:",
            parse_mode="HTML",
            reply_markup=admin_support_tickets_kb(tickets)
        )
    await callback.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("admin_support_ticket_") and not c.data.startswith("admin_support_ticket_delete_"))
async def admin_support_ticket_detail(callback: types.CallbackQuery):
    """Показать детали тикета и действия"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    if not callback.data:
        await callback.answer("❌ Нет данных", show_alert=True)
        return
    ticket_id = int(callback.data.replace("admin_support_ticket_", ""))
    ticket = get_support_ticket_by_id(ticket_id)
    if not ticket:
        await callback.answer("❌ Тикет не найден", show_alert=True)
        return
    # Получаем профиль пользователя для получения Telegram ID
    user_profile = get_user_profile_by_id(ticket['user_id'])
    user_display = f"@{ticket['username']}" if ticket['username'] else ticket['full_name']
    user_tg_id = user_profile['tg_id'] if user_profile else "неизвестен"

    text = (
        f"✅ <b>Тикет #{ticket['id']}</b>\n"
        f"👤 <b>Пользователь:</b> {user_display}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_tg_id}</code>\n"
        f"📝 <b>Сообщение:</b> {ticket['message']}\n"
        f"📅 <b>Статус:</b> {ticket['status']}\n"
    )
    if callback.message and hasattr(callback.message, 'answer'):
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=admin_support_ticket_actions_kb(ticket_id)
        )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_support_ticket_delete_"))
async def admin_support_ticket_delete(callback: types.CallbackQuery):
    """Удалить тикет поддержки по номеру"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    if not callback.data:
        await callback.answer("❌ Нет данных", show_alert=True)
        return
    ticket_id = int(callback.data.replace("admin_support_ticket_delete_", ""))
    ticket = get_support_ticket_by_id(ticket_id)
    if not ticket:
        await callback.answer("❌ Тикет не найден", show_alert=True)
        return
    try:
        delete_support_ticket(ticket_id)
        if callback.message and hasattr(callback.message, 'answer'):
            await callback.message.answer(f"✅ Тикет #{ticket_id} удалён.")
    except Exception as e:
        logger.error(f"[SUPPORT] Ошибка удаления тикета: {e}")
        if callback.message and hasattr(callback.message, 'answer'):
            await callback.message.answer(f"❌ Ошибка удаления тикета #{ticket_id}.")
    await callback.answer()

@router.callback_query(F.data == "admin_clear_all_tickets")
async def admin_clear_all_tickets(callback: types.CallbackQuery):
    """Подтверждение удаления всех тикетов"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    if callback.message and hasattr(callback.message, 'answer'):
        await callback.message.answer(
            "⚠️ Вы уверены, что хотите удалить ВСЕ тикеты поддержки?\n\n"
            "Это действие нельзя отменить!",
            reply_markup=admin_clear_all_tickets_kb()
        )
    await callback.answer()

@router.callback_query(F.data == "admin_clear_all_tickets_confirm")
async def admin_clear_all_tickets_confirm(callback: types.CallbackQuery):
    """Подтверждение удаления всех тикетов"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    try:
        clear_all_support_tickets()
        if callback.message and hasattr(callback.message, 'answer'):
            await callback.message.answer("✅ Все тикеты поддержки удалены.")
    except Exception as e:
        logger.error(f"[SUPPORT] Ошибка удаления всех тикетов: {e}")
        if callback.message and hasattr(callback.message, 'answer'):
            await callback.message.answer("❌ Ошибка при удалении тикетов.")
    await callback.answer()
