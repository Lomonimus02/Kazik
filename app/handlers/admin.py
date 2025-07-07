"""
Админские обработчики - финальная исправленная версия
"""
import logging
import json
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.config import ADMINS
from app.database.models import (
    get_all_pending_withdrawals, get_withdrawal_by_id, update_withdrawal_status,
    get_all_orders, get_order_by_id, update_order_status, delete_order, clear_all_orders,
    get_all_reviews, update_review_status, delete_review, clear_all_reviews,
    get_user_profile_by_id, add_stars_to_user, add_ton_to_user, update_balance,
    add_referral_bonus_for_order_async, get_flag, get_all_users, get_review_by_id
)

router = Router()

class AdminStates(StatesGroup):
    waiting_for_value = State()
    waiting_for_user_id = State()
    waiting_for_amount = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

async def check_admin_access(handler, message_or_callback):
    """Проверка прав администратора с обработкой ошибок"""
    try:
        if not hasattr(message_or_callback, 'from_user') or not hasattr(message_or_callback.from_user, 'id'):
            logging.error("Admin access check failed: invalid message/callback object")
            return False
            
        if not is_admin(message_or_callback.from_user.id):
            if isinstance(message_or_callback, types.CallbackQuery):
                await message_or_callback.answer("❌ Доступ запрещен")
            else:
                await message_or_callback.answer("❌ Доступ запрещен")
            return False
        return True
    except Exception as e:
        logging.error(f"Error in admin access check: {e}")
        return False

@router.message(Command("admin"))
async def admin_menu(message: types.Message):
    if not await check_admin_access(admin_menu, message):
        return
    
    text = "👑 <b>Админ-панель</b>\n\nВыберите раздел:"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")],
        [InlineKeyboardButton(text="📋 Заявки", callback_data="admin_orders")],
        [InlineKeyboardButton(text="📝 Отзывы", callback_data="admin_reviews")],
        [InlineKeyboardButton(text="🎰 Слот-машина", callback_data="admin_slot_settings")],
        [InlineKeyboardButton(text="👤 Управление пользователями", callback_data="admin_users")],
    ])
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "admin_users")
async def admin_users_menu(callback: types.CallbackQuery):
    if not await check_admin_access(admin_users_menu, callback):
        return
    
    text = "👤 <b>Управление пользователями</b>\n\nВыберите действие:"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Список пользователей", callback_data="admin_users_list")],
        [InlineKeyboardButton(text="➕ Добавить баланс", callback_data="admin_add_balance")],
        [InlineKeyboardButton(text="➖ Списать баланс", callback_data="admin_remove_balance")],
        [InlineKeyboardButton(text="⭐ Добавить звезды", callback_data="admin_add_stars")],
        [InlineKeyboardButton(text="💎 Добавить TON", callback_data="admin_add_ton")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")],
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "admin_users_list")
async def admin_users_list(callback: types.CallbackQuery):
    if not await check_admin_access(admin_users_list, callback):
        return
    
    try:
        users = get_all_users()
        if not users:
            await callback.message.answer("📭 Нет пользователей в базе")
            return
            
        text = "👥 <b>Список пользователей</b>\n\n"
        for user in users[:15]:
            text += (
                f"ID: {user[1]}\n"
                f"Имя: {user[2]}\n"
                f"Юзернейм: @{user[3] if user[3] else 'нет'}\n"
                f"Баланс: {user[5]} RUB\n"
                f"Заморожено: {user[6]} RUB\n"
                f"Дата регистрации: {user[4]}\n\n"
            )
            
        if len(users) > 15:
            text += f"\n...и еще {len(users)-15} пользователей"
            
        await callback.message.answer(text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Error in admin_users_list: {e}")
        await callback.message.answer("❌ Ошибка при получении списка пользователей")

@router.callback_query(F.data.startswith("admin_add_"))
async def admin_balance_action(callback: types.CallbackQuery, state: FSMContext):
    if not await check_admin_access(admin_balance_action, callback):
        return
    
    action = callback.data.split("_")[-1]
    await state.update_data(action=action)
    await state.set_state(AdminStates.waiting_for_user_id)
    
    action_text = {
        "balance": "баланс",
        "stars": "звёзды",
        "ton": "TON"
    }.get(action, "баланс")
    
    await callback.message.answer(
        f"✏️ Введите ID пользователя для изменения {action_text}:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_users")]]
        )
    )

@router.message(AdminStates.waiting_for_user_id)
async def process_user_id(message: types.Message, state: FSMContext):
    if not await check_admin_access(process_user_id, message):
        return
    
    try:
        user_id = int(message.text)
        user = get_user_profile_by_id(user_id)
        
        if not user:
            await message.answer("❌ Пользователь не найден. Попробуйте еще раз:")
            return
            
        data = await state.get_data()
        action = data.get('action', 'balance')
        await state.update_data(user_id=user_id)
        await state.set_state(AdminStates.waiting_for_amount)
        
        currency = {
            'balance': 'RUB',
            'stars': 'звёзд',
            'ton': 'TON'
        }.get(action, 'RUB')
        
        await message.answer(
            f"💰 Введите количество {currency} для добавления:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_users")]]
            )
        )
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите числовой ID пользователя:")

@router.message(AdminStates.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    if not await check_admin_access(process_amount, message):
        return
    
    try:
        amount = float(message.text)
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше нуля. Введите корректное значение:")
            return
            
        data = await state.get_data()
        user_id = data.get('user_id')
        action = data.get('action', 'balance')
        
        user = get_user_profile_by_id(user_id)
        if not user:
            await message.answer("❌ Пользователь не найден. Операция отменена.")
            await state.clear()
            return
            
        if action == 'balance':
            update_balance(user['tg_id'], amount)
        elif action == 'stars':
            add_stars_to_user(user['tg_id'], amount)
        elif action == 'ton':
            add_ton_to_user(user['tg_id'], amount)
            
        await message.answer(
            f"✅ Успешно! Пользователю {user['full_name']} (ID: {user['tg_id']}) "
            f"добавлено {amount} {'RUB' if action == 'balance' else 'звёзд' if action == 'stars' else 'TON'}"
        )
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат суммы. Введите число:")

# Остальные обработчики остаются без изменений...

@router.message(Command("orders"))
async def show_orders(message: types.Message):
    if not await check_admin_access(show_orders, message):
        return
    
    try:
        orders = get_all_orders()
        if not orders:
            await message.answer("📋 Нет активных заявок.")
            return
            
        text = "📋 <b>Активные заявки:</b>\n\n"
        for order in orders[:10]:
            order_id, user_id, order_type, amount, status, created_at, file_id, extra_data = order
            type_emoji = {
                "withdraw": "💰",
                "premium": "⭐",
                "stars": "🌟",
                "crypto": "₿",
                "activity_reward": "🎁",
                "slot_win": "🎰"
            }.get(order_type, "📋")
            
            type_label = {
                "activity_reward": "Календарь активности",
                "slot_win": "Рулетка",
                "withdraw": "Вывод",
                "premium": "Премиум",
                "stars": "Звёзды",
                "crypto": "Крипта"
            }.get(order_type, order_type)
            
            text += (
                f"{type_emoji} <b>Заявка #{order_id}</b>\n"
                f"👤 Пользователь: ID {user_id}\n"
                f"📊 Тип: {type_label}\n"
                f"💰 Сумма: <b>{amount}</b>\n"
                f"📝 Статус: {status}\n"
                f"⏰ Время: {created_at}\n"
                f"Описание: {extra_data}\n\n"
            )
            
        if len(orders) > 10:
            text += f"... и еще {len(orders) - 10} заявок"
            
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Error in show_orders: {e}")
        await message.answer("❌ Ошибка при получении списка заявок")

@router.callback_query(F.data.startswith("order_approve_"))
async def order_approve(callback: types.CallbackQuery):
    if not await check_admin_access(order_approve, callback):
        return
    
    try:
        order_id = int(callback.data.split("_")[2])
        order = get_order_by_id(order_id)
        
        if not order:
            await callback.answer("❌ Заявка не найдена")
            return
            
        # Обновляем статус заявки
        update_order_status(order_id, 'approved', callback.message.message_id)
        
        # Обработка реферального бонуса
        from app.utils.misc import process_referral_bonus
        try:
            await process_referral_bonus(callback.bot, order['user_id'], order['amount'], order['order_type'], order_id)
        except Exception as e:
            logging.error(f"Ошибка обработки реферального бонуса: {e}")
        
        # Уведомление пользователя
        user_profile = get_user_profile_by_id(order['user_id'])
        if user_profile:
            try:
                await callback.bot.send_message(
                    user_profile['tg_id'],
                    f"✅ Ваша заявка #{order_id} подтверждена!\n"
                    f"Тип: {order['order_type']}\n"
                    f"Сумма: {order['amount']}"
                )
            except Exception as e:
                logging.error(f"Error notifying user: {e}")
                
        await callback.answer("✅ Заявка подтверждена")
        await callback.message.edit_text(f"✅ Заявка #{order_id} подтверждена")
    except Exception as e:
        logging.error(f"Error in order_approve: {e}")
        await callback.answer("❌ Ошибка при подтверждении заявки")

@router.callback_query(F.data.startswith("order_delete_"))
async def order_delete(callback: types.CallbackQuery):
    if not await check_admin_access(order_delete, callback):
        return
    
    try:
        order_id = int(callback.data.split("_")[2])
        delete_order(order_id)
        await callback.answer("🗑 Заявка удалена")
        await callback.message.edit_text(f"🗑 Заявка #{order_id} удалена")
    except Exception as e:
        logging.error(f"Error in order_delete: {e}")
        await callback.answer("❌ Ошибка при удалении заявки")

@router.message(Command("clear_orders"))
async def clear_orders(message: types.Message):
    if not await check_admin_access(clear_orders, message):
        return
    
    try:
        clear_all_orders()
        await message.answer("🗑 Все заявки очищены.")
    except Exception as e:
        logging.error(f"Error in clear_orders: {e}")
        await message.answer("❌ Ошибка при очистке заявок")

@router.message(Command("reviews"))
async def show_reviews(message: types.Message):
    if not await check_admin_access(show_reviews, message):
        return
    
    try:
        reviews = get_all_reviews()
        if not reviews:
            await message.answer("📝 Нет отзывов.")
            return
            
        text = "📝 <b>Отзывы:</b>\n\n"
        for review in reviews[:10]:
            review_id, user_id, content, status, created_at, file_id, admin_msg_id, channel_msg_id = review
            text += (
                f"💬 <b>Отзыв #{review_id}</b>\n"
                f"👤 Пользователь: ID {user_id}\n"
                f"📝 Статус: {status}\n"
                f"⏰ Время: {created_at}\n"
                f"💭 Текст: {content[:100]}{'...' if len(content) > 100 else ''}\n\n"
            )
            
        if len(reviews) > 10:
            text += f"... и еще {len(reviews) - 10} отзывов"
            
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Error in show_reviews: {e}")
        await message.answer("❌ Ошибка при получении отзывов")

@router.callback_query(F.data.startswith("review_reject_"))
async def review_reject(callback: types.CallbackQuery):
    if not await check_admin_access(review_reject, callback):
        return
    
    try:
        review_id = int(callback.data.split("_")[2])
        update_review_status(review_id, 'rejected', callback.message.message_id)
        
        # Уведомление пользователя
        review = get_review_by_id(review_id)
        if review:
            try:
                await callback.bot.send_message(
                    review['user_id'],
                    "❌ Ваш отзыв был отклонен администратором."
                )
            except Exception as e:
                logging.error(f"Error notifying user about rejected review: {e}")
                
        await callback.answer("❌ Отзыв отклонен")
        await callback.message.edit_text(f"❌ Отзыв #{review_id} отклонен")
    except Exception as e:
        logging.error(f"Error in review_reject: {e}")
        await callback.answer("❌ Ошибка при отклонении отзыва")

@router.callback_query(F.data == "admin_reviews")
async def admin_reviews_menu(callback: types.CallbackQuery):
    """Админское меню управления отзывами"""
    if not await check_admin_access(admin_reviews_menu, callback):
        return

    try:
        reviews = get_all_reviews()

        text = "📝 <b>УПРАВЛЕНИЕ ОТЗЫВАМИ</b>\n\n"

        if not reviews:
            text += "📝 Нет отзывов в системе.\n\n"
        else:
            # Статистика по статусам
            pending_count = len([r for r in reviews if r[3] == 'pending'])
            published_count = len([r for r in reviews if r[3] == 'published'])
            rejected_count = len([r for r in reviews if r[3] == 'rejected'])

            text += f"📊 <b>Статистика:</b>\n"
            text += f"• Всего отзывов: {len(reviews)}\n"
            text += f"• ⏳ На модерации: {pending_count}\n"
            text += f"• ✅ Опубликованы: {published_count}\n"
            text += f"• ❌ Отклонены: {rejected_count}\n\n"

            # Показываем последние 5 отзывов
            text += "📋 <b>Последние отзывы:</b>\n"
            for review in reviews[:5]:
                review_id, user_id, content, status, created_at, file_id, admin_msg_id, channel_msg_id = review
                status_emoji = {"pending": "⏳", "published": "✅", "rejected": "❌"}
                status_icon = status_emoji.get(status, "❔")

                text += f"#{review_id} {status_icon} | ID:{user_id} | {content[:30]}...\n"

            if len(reviews) > 5:
                text += f"... и еще {len(reviews) - 5} отзывов\n"

        # Клавиатура с функциями
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Все отзывы", callback_data="admin_all_reviews"),
                InlineKeyboardButton(text="⏳ На модерации", callback_data="admin_pending_reviews")
            ],
            [
                InlineKeyboardButton(text="➕ Добавить отзыв", callback_data="add_review"),
                InlineKeyboardButton(text="🗑 Очистить все", callback_data="admin_clear_reviews")
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")
            ]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logging.error(f"Error in admin_reviews_menu: {e}")
        await callback.answer("❌ Ошибка при загрузке отзывов", show_alert=True)

@router.callback_query(F.data == "admin_all_reviews")
async def admin_all_reviews(callback: types.CallbackQuery):
    """Показать все отзывы"""
    if not await check_admin_access(admin_all_reviews, callback):
        return

    try:
        reviews = get_all_reviews()
        if not reviews:
            await callback.answer("📝 Нет отзывов", show_alert=True)
            return

        text = "📝 <b>ВСЕ ОТЗЫВЫ:</b>\n\n"
        for review in reviews[:10]:
            review_id, user_id, content, status, created_at, file_id, admin_msg_id, channel_msg_id = review
            status_emoji = {"pending": "⏳", "published": "✅", "rejected": "❌"}
            status_icon = status_emoji.get(status, "❔")

            text += (
                f"💬 <b>Отзыв #{review_id}</b> {status_icon}\n"
                f"👤 Пользователь: ID {user_id}\n"
                f"📝 Статус: {status}\n"
                f"⏰ Время: {created_at}\n"
                f"💭 Текст: {content[:100]}{'...' if len(content) > 100 else ''}\n\n"
            )

        if len(reviews) > 10:
            text += f"... и еще {len(reviews) - 10} отзывов"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_reviews")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logging.error(f"Error in admin_all_reviews: {e}")
        await callback.answer("❌ Ошибка при получении отзывов", show_alert=True)

@router.callback_query(F.data == "admin_pending_reviews")
async def admin_pending_reviews(callback: types.CallbackQuery):
    """Показать отзывы на модерации"""
    if not await check_admin_access(admin_pending_reviews, callback):
        return

    try:
        all_reviews = get_all_reviews()
        pending_reviews = [r for r in all_reviews if r[3] == 'pending']

        if not pending_reviews:
            await callback.answer("⏳ Нет отзывов на модерации", show_alert=True)
            return

        text = "⏳ <b>ОТЗЫВЫ НА МОДЕРАЦИИ:</b>\n\n"
        for review in pending_reviews[:10]:
            review_id, user_id, content, status, created_at, file_id, admin_msg_id, channel_msg_id = review

            text += (
                f"💬 <b>Отзыв #{review_id}</b>\n"
                f"👤 Пользователь: ID {user_id}\n"
                f"⏰ Время: {created_at}\n"
                f"💭 Текст: {content[:150]}{'...' if len(content) > 150 else ''}\n\n"
            )

        if len(pending_reviews) > 10:
            text += f"... и еще {len(pending_reviews) - 10} отзывов"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_reviews")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logging.error(f"Error in admin_pending_reviews: {e}")
        await callback.answer("❌ Ошибка при получении отзывов", show_alert=True)

@router.callback_query(F.data == "admin_clear_reviews")
async def admin_clear_reviews_confirm(callback: types.CallbackQuery):
    """Подтверждение очистки всех отзывов"""
    if not await check_admin_access(admin_clear_reviews_confirm, callback):
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, очистить", callback_data="admin_clear_reviews_confirmed"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_reviews")
        ]
    ])

    await callback.message.edit_text(
        "⚠️ <b>ВНИМАНИЕ!</b>\n\n"
        "Вы действительно хотите удалить ВСЕ отзывы?\n"
        "Это действие нельзя отменить!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_clear_reviews_confirmed")
async def admin_clear_reviews_execute(callback: types.CallbackQuery):
    """Выполнение очистки всех отзывов"""
    if not await check_admin_access(admin_clear_reviews_execute, callback):
        return

    try:
        clear_all_reviews()
        await callback.message.edit_text(
            "🗑 <b>Все отзывы успешно удалены!</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_reviews")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer("✅ Отзывы очищены")

    except Exception as e:
        logging.error(f"Error in admin_clear_reviews_execute: {e}")
        await callback.answer("❌ Ошибка при очистке отзывов", show_alert=True)

@router.message(Command("clear_reviews"))
async def clear_reviews(message: types.Message):
    if not await check_admin_access(clear_reviews, message):
        return

    try:
        clear_all_reviews()
        await message.answer("🗑 Все отзывы очищены.")
    except Exception as e:
        logging.error(f"Error in clear_reviews: {e}")
        await message.answer("❌ Ошибка при очистке отзывов")

@router.callback_query(F.data == "admin_orders_page:0")
async def admin_orders_first_page(callback: types.CallbackQuery):
    await admin_orders_page_callback(callback)

@router.callback_query(F.data.startswith("admin_orders_page:"))
async def admin_orders_page_callback(callback: types.CallbackQuery):
    if not await check_admin_access(admin_orders_page_callback, callback):
        return
    
    try:
        page = int(callback.data.split(":")[1])
        orders = get_all_orders()
        per_page = 5
        total_pages = (len(orders) + per_page - 1) // per_page
        start = page * per_page
        end = start + per_page
        orders_page = orders[start:end]
        
        if not orders_page:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")],
            ])
            await callback.message.answer("📋 Нет заявок.", reply_markup=kb)
            return
            
        text = f"<b>ЗАЯВКИ (стр. {page+1} из {total_pages}):</b>\n\n"
        status_emoji = {"pending": "⏳", "completed": "✅", "rejected": "❌"}
        type_icons = {
            "premium": "⭐️", "stars": "🌟", "crypto": "🪙", 
            "withdraw": "💸", "slot_win": "🎰", "activity_reward": "🎁"
        }
        
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
                extra = json.loads(extra_data) if extra_data else {}
                if order_type == 'premium':
                    text += f"📅 Период: {extra.get('period','-')}\n"
                    text += f"🎁 Получатель: {extra.get('recipient','-')}\n"
                elif order_type == 'stars':
                    text += f"⭐ Количество: {extra.get('amount','-')}\n"
                    text += f"🎁 Получатель: {extra.get('recipient','-')}\n"
                elif order_type == 'crypto':
                    text += f"🪙 Монета: {extra.get('coin','-')}\n"
                    text += f"📊 Количество: {extra.get('amount','-')}\n"
                    text += f"🏦 Кошелёк: {extra.get('wallet','-')}\n"
                elif order_type == 'withdraw':
                    text += f"💳 Реквизиты: {extra.get('requisites','-')}\n"
            except Exception:
                pass
                
            text += f"⏰ Время: {created_at}\n\n"
            
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_orders_page:{page-1}"))
        if (page + 1) < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="➡️ Вперёд", callback_data=f"admin_orders_page:{page+1}"))
            
        nav_buttons.append(InlineKeyboardButton(text="🏠 В меню", callback_data="admin_panel"))
        
        kb = InlineKeyboardMarkup(inline_keyboard=[nav_buttons])
        await callback.message.delete()
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logging.error(f"Error in admin_orders_page_callback: {e}")
        await callback.answer("❌ Ошибка при загрузке страницы заявок")