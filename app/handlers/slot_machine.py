"""
Обработчики слот-машины с проверкой подписки и системой бонусных попыток
"""
import asyncio
import datetime
import logging
import random
import aiosqlite 
from typing import Tuple, Optional

from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.types.message import Message

from app.database.models import get_slot_configs
from app.config import ADMINS
from app.database.models import (
    get_user_slot_spins, get_slot_wins, get_slot_wins_async, update_slot_win_status,
    get_admin_setting, create_slot_win, create_order, update_balance,
    get_slot_configs, get_user_profile, should_reset_daily_attempts,
    use_slot_spin, reset_slot_spins, get_slot_win_by_id, add_stars_to_user, add_ton_to_user,
    get_user_roulette_attempts, use_roulette_attempt, reset_roulette_attempts, get_roulette_configs
)
from app.keyboards.main import slot_machine_kb, slot_win_admin_kb
from app.utils.slot_machine import (
    format_slot_result, generate_slot_result, check_win_combination,
    animate_slot_machine, process_slot_win, notify_admins_slot_win
)

router = Router()

# Эмодзи для слот-машины (используются для анимации)
SLOT_EMOJIS = ["🍒", "🍋", "🍊", "🍇", "⭐️", "💎", "🔔", "💰", "🎰", "7️⃣"]

# Настройки канала для проверки подписки
CHANNEL_ID = -1002680464877
CHANNEL_USERNAME = "@legal_stars"
CHANNEL_LINK = "https://t.me/legal_stars"

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

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
        "Для доступа к этому разделу необходимо подписаться на наш канал.\n\n"
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

async def get_user_attempts(user_id: int) -> Tuple[int, int]:
    """Возвращает (использованные попытки, бонусные попытки)"""
    async with aiosqlite.connect('data/users.db') as db:
        # Стандартные попытки
        cursor = await db.execute(
            "SELECT attempts_used FROM roulette_attempts WHERE user_id = ?",
            (user_id,)
        )
        attempts_used = (await cursor.fetchone() or [0])[0]
        
        # Бонусные попытки
        cursor = await db.execute(
            "SELECT attempts FROM bonus_attempts WHERE user_id = ?",
            (user_id,)
        )
        bonus_attempts = (await cursor.fetchone() or [0])[0]
        
    return attempts_used, bonus_attempts

async def use_slot_attempt(user_id: int) -> bool:
    """Использует одну попытку (сначала бонусные, потом стандартные)"""
    async with aiosqlite.connect('data/users.db') as db:
        # Проверяем бонусные попытки
        cursor = await db.execute(
            "SELECT attempts FROM bonus_attempts WHERE user_id = ?",
            (user_id,)
        )
        bonus = (await cursor.fetchone() or [0])[0]
        
        if bonus > 0:
            # Используем бонусную попытку
            await db.execute(
                "UPDATE bonus_attempts SET attempts = attempts - 1 WHERE user_id = ?",
                (user_id,)
            )
        else:
            # Используем стандартную попытку
            await db.execute(
                "UPDATE roulette_attempts SET attempts_used = attempts_used + 1 WHERE user_id = ?",
                (user_id,)
            )
        
        await db.commit()
        return True

@router.callback_query(F.data == "slot_machine")
async def slot_machine_menu(callback: types.CallbackQuery):
    """Главное меню слот-машины"""
    try:
        user_id = callback.from_user.id

        # 1. Проверка черного списка
        from app.handlers.user import check_blacklist_and_respond
        if await check_blacklist_and_respond(user_id, callback):
            return

        # 2. Проверка подписки (обязательная для слот-машинки)
        if not await check_subscription(user_id, callback.bot):
            await show_subscription_message(callback, callback.bot)
            return
        
        # 2. Получаем данные о попытках (асинхронные)
        today = datetime.date.today().isoformat()
        roulette_data = await get_user_roulette_attempts(user_id)
        attempts_used = roulette_data[0] if roulette_data else 0
        last_reset = roulette_data[1] if roulette_data else None
        
        # 3. Сброс попыток если нужно (асинхронная)
        if last_reset != today:
            await reset_roulette_attempts(user_id)
            attempts_used = 0
        
        # 4. Получаем попытки слот-машины (стандартные и бонусные)
        attempts_used, bonus_attempts = await get_user_attempts(user_id)

        # 5. Сброс попыток если нужно
        slot_data = get_user_slot_spins(user_id)
        last_reset = slot_data[1] if slot_data else None
        if should_reset_daily_attempts(last_reset):
            reset_slot_spins(user_id)
            attempts_used = 0
        
        # 5. Получаем настройки слот-машины из админ панели
        daily_attempts_str = get_admin_setting('slot_daily_attempts', '5')
        daily_attempts = int(daily_attempts_str) if daily_attempts_str and daily_attempts_str.isdigit() else 5
        slot_description = get_admin_setting('slot_description', '🎰 <b>Слот-машина</b>\n\nСлот-машина — это бесплатная игра от Legal Stars.\n\n🎁Выигрывайте деньги, звёзды и TON!')
        slot_photo = get_admin_setting('slot_photo', 'https://imgur.com/a/TkOPe7c.jpeg')

        # 7. Получаем информацию о рефералах
        from app.database.models import get_user_profile, get_unclaimed_referrals_count
        user_profile = get_user_profile(user_id)
        unclaimed_referrals = 0
        if user_profile:
            try:
                unclaimed_referrals = await get_unclaimed_referrals_count(user_profile['id'])
            except Exception as e:
                logging.error(f"Ошибка получения неактивированных рефералов: {e}")

        # 8. Формируем текст
        remaining_standard = max(0, daily_attempts - attempts_used)
        text = (
            f"{slot_description}\n\n"
            f"🔄 Сброс попыток: каждый день в 00:00 по МСК\n"
            f"🎯 Попыток сегодня: {remaining_standard}/{daily_attempts} (стандартные)\n"
            f"🎁 Бонусные попытки: {bonus_attempts}\n"
            f"👥 Неактивированных рефералов: {unclaimed_referrals}"
        )

        # 9. Создаем клавиатуру
        referral_button_text = f"🎁 Получить бонус ({unclaimed_referrals})" if unclaimed_referrals > 0 else "🎁 Получить бонус"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎰 Крутить слоты", callback_data="spin_slot")],
            [InlineKeyboardButton(text=referral_button_text, callback_data="claim_referral_bonus")],
            [InlineKeyboardButton(text="🏆 Список наград", callback_data="slot_prizes")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="slot_stats")],
            [InlineKeyboardButton(text="🎁 Мои призы", callback_data="my_prizes")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
        ])

        # 10. Удаляем предыдущее сообщение и отправляем новое с фото
        try:
            await callback.message.delete()
        except:
            pass

        await callback.message.answer_photo(
            photo=slot_photo,
            caption=text,
            reply_markup=kb,
            parse_mode="HTML"
        )
    
    except Exception as e:
        logging.error(f"Error in slot_machine_menu: {str(e)}", exc_info=True)
        await callback.answer("⚠️ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "my_prizes")
async def my_prizes_handler(callback: types.CallbackQuery):
    """Показывает выигранные призы пользователя"""
    try:
        user_id = callback.from_user.id

        # Получаем ВСЕ выигрыши пользователя (включая автоматически начисленные деньги)
        # Изменяем запрос: получаем все выигрыши где is_win=True, независимо от статуса
        wins = await get_slot_wins_async(user_id=user_id)

        # Фильтруем только выигрыши (is_win=True или 1)
        actual_wins = [win for win in wins if win[7] in (True, 1)]  # win[7] = is_win

        if not actual_wins:
            text = (
                "🎁 <b>Ваши выигранные призы</b>\n\n"
                "У вас пока нет выигранных призов.\n\n"
                "🎰 Крутите слоты, чтобы выиграть призы!"
            )
        else:
            text = "🎁 <b>Ваши выигранные призы</b>\n\n"

            # Получаем конфигурации из БД для правильного отображения
            slot_configs = get_slot_configs()

            for win in actual_wins[-10:]:  # Последние 10 призов
                combination = win[4]     # sm.combination
                reward_type = win[5]     # sm.reward_type
                reward_amount = win[6]   # sm.reward_amount
                created_at = win[8] if len(win) > 8 else "Неизвестно"  # sm.created_at
                status = win[9] if len(win) > 9 else "pending"  # sm.status

                # Находим название приза из конфигурации БД
                prize_name = combination
                for config in slot_configs:
                    if config[1] == combination:  # config[1] = combination
                        prize_name = config[6]  # config[6] = name
                        break

                if reward_type == "money":
                    reward_text = f"{int(reward_amount)}₽"
                    status_text = "✅ Зачислено"  # Деньги зачисляются автоматически
                elif reward_type == "stars":
                    reward_text = f"{int(reward_amount)}⭐️"
                    status_text = "✅ Зачислено" if status == "completed" else "⏳ Ожидает подтверждения"
                elif reward_type == "ton":
                    reward_text = f"{reward_amount} TON"
                    status_text = "✅ Зачислено" if status == "completed" else "⏳ Ожидает подтверждения"
                else:
                    reward_text = str(reward_amount)
                    status_text = "✅ Зачислено" if status == "completed" else "⏳ Ожидает подтверждения"

                # Форматируем дату
                try:
                    if isinstance(created_at, str) and len(created_at) >= 10:
                        date_part = created_at[:10]
                    else:
                        date_part = str(created_at)[:10] if created_at else "Неизвестно"
                except:
                    date_part = "Неизвестно"

                text += f"🏆 {prize_name}\n💰 {reward_text}\n📊 {status_text}\n📅 {date_part}\n\n"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎰 Крутить слоты", callback_data="spin_slot")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="slot_machine")]
        ])
        
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            # Если не удалось отредактировать, отправляем новое сообщение
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка в my_prizes_handler: {e}")
        await callback.answer("⚠️ Произошла ошибка. Попробуйте позже.", show_alert=True)

@router.callback_query(F.data == "spin_slot")
async def spin_slot_machine(callback: types.CallbackQuery):
    """Вращение слот-машины с обработкой ошибок"""
    user_id = callback.from_user.id
    user = callback.from_user

    try:
        # Проверка черного списка
        from app.handlers.user import check_blacklist_and_respond
        if await check_blacklist_and_respond(user_id, callback):
            return

        # Проверка подписки (обязательная для слот-машинки)
        if not await check_subscription(user_id, callback.bot):
            await show_subscription_message(callback, callback.bot)
            return

        # Получаем текущие попытки
        attempts_used, bonus_attempts = await get_user_attempts(user_id)
        daily_attempts = int(get_admin_setting('slot_daily_attempts', '5'))
        remaining_standard = max(0, daily_attempts - attempts_used)
        total_available = remaining_standard + bonus_attempts
        
        if total_available <= 0:
            text = (
                "🎰 <b>СЛОТ-МАШИНА</b> 🎰\n\n"
                "🔴 <b>У вас закончились попытки!</b>\n\n"
                f"🔄 Попытки обновятся в 00:00 по МСК\n\n"
                f"💡 Вы можете получить бонусные попытки:\n"
                f"• Приглашая друзей\n"
                f"• За ежедневный вход\n"
                f"• За выполнение заданий"
            )
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="slot_machine")],
                [InlineKeyboardButton(text="🔄 Проверить попытки", callback_data="spin_slot")]
            ])
            
            try:
                await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except:
                await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
            return
        
        # Используем попытку (сначала бонусные)
        await use_slot_attempt(user_id)
        
        # Создаем сообщение с анимацией
        anim_message = await callback.message.answer(
            "🎰 <b>СЛОТ-МАШИНА КРУТИТСЯ...</b> 🎰\n\n"
            "        ┌─────────────┐\n"
            "        │  🎰  │  🎰  │  🎰  │\n"
            "        └─────────────┘\n\n"
            "🎯 Подготовка к вращению..."
        )

        # Используем правильную анимацию и генерацию из utils
        slot1, slot2, slot3 = await animate_slot_machine(anim_message, callback)

        # Проверяем выигрышную комбинацию используя БД
        win_config = await check_win_combination(slot1, slot2, slot3)

        if win_config:
            # Обрабатываем выигрыш используя правильную логику из utils
            config_id, combination, reward_type, reward_amount, chance_percent, emoji, prize_name = win_config

            # Обрабатываем выигрыш через правильную функцию
            reward_text, win_id = await process_slot_win(user_id, win_config)

            # Формируем текст выигрыша используя правильный формат
            result_text = format_slot_result(
                slot1, slot2, slot3, True, reward_text, prize_name, reward_type
            )

            # Отправляем уведомление админам только для stars и ton (деньги начисляются автоматически)
            if reward_type in ["stars", "ton"]:
                try:
                    await notify_admins_slot_win(user_id, combination, reward_type, reward_amount, callback.bot)
                except Exception as e:
                    logging.error(f"Ошибка уведомления админам: {e}")
        else:
            # Создаем запись о проигрыше
            combination = slot1 + slot2 + slot3
            create_slot_win(user_id, combination, "none", 0, False)

            # Формируем текст проигрыша
            result_text = format_slot_result(slot1, slot2, slot3, False)
        
        # Обновляем информацию о попытках
        attempts_used, bonus_attempts = await get_user_attempts(user_id)
        remaining_standard = max(0, daily_attempts - attempts_used)
        total_remaining = remaining_standard + bonus_attempts
        
        result_text += (
            f"\n\n🎯 <b>Осталось попыток:</b>\n"
            f"• Стандартные: {remaining_standard}/{daily_attempts}\n"
            f"• Бонусные: {bonus_attempts}\n"
            f"• Всего: {total_remaining}"
        )
        
        # Клавиатура результата
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎰 Крутить ещё раз", callback_data="spin_slot")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="slot_machine")]
        ])
        
        try:
            await anim_message.edit_text(result_text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Ошибка отображения результата: {e}")
            await callback.message.answer(result_text, reply_markup=kb, parse_mode="HTML")
    
    except Exception as e:
        logging.error(f"Ошибка в слот-машине: {e}", exc_info=True)
        await callback.answer("⚠️ Произошла ошибка при обработке запроса. Попробуйте позже.", show_alert=True)

@router.callback_query(F.data.startswith("slot_win_confirm_"))
async def slot_win_confirm_handler(callback: types.CallbackQuery):
    """Подтверждение выигрыша слот-машины"""
    import datetime
    import json

    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return

    try:
        # Получаем ID выигрыша
        win_id = int(callback.data.replace("slot_win_confirm_", ""))

        # Получаем данные выигрыша из БД
        win_data_db = get_slot_win_by_id(win_id)
        if not win_data_db:
            await callback.answer("❌ Выигрыш не найден")
            return

        # Парсим данные выигрыша (с учетом нового поля extra_data)
        win_data = {
            'id': win_data_db[0],           # sm.id
            'user_id': win_data_db[1],      # sm.user_id
            'tg_id': win_data_db[2],        # u.tg_id
            'full_name': win_data_db[3],    # u.full_name
            'combination': win_data_db[4],  # sm.combination
            'reward_type': win_data_db[5],  # sm.reward_type
            'reward_amount': win_data_db[6], # sm.reward_amount
            'is_win': win_data_db[7],       # sm.is_win
            'created_at': win_data_db[8],   # sm.created_at
            'status': win_data_db[9],       # sm.status
            'extra_data': win_data_db[10] if len(win_data_db) > 10 else None  # sm.extra_data
        }

        confirm_time = datetime.datetime.now().strftime('%H:%M %d.%m.%Y')
        admin_username = f"@{callback.from_user.username}" if callback.from_user.username else f"ID {callback.from_user.id}"

        # Извлекаем данные
        user_id = win_data['user_id']
        combination = win_data['combination']
        reward_type = win_data['reward_type']
        reward_amount = win_data['reward_amount']
        created_at = win_data.get('created_at', datetime.datetime.now().strftime('%d.%m.%Y %H:%M'))

        # Получаем информацию о пользователе
        try:
            user_profile = get_user_profile(user_id)
            if user_profile:
                username = user_profile.get('username', f"ID {user_id}")
            else:
                username = f"ID {user_id}"
        except Exception as e:
            logging.warning(f"[SLOT] Ошибка получения профиля {user_id}: {e}")
            username = f"ID {user_id}"

        user_mention = f"@{username}" if username.startswith("@") else username

        # Находим информацию о комбинации в БД
        slot_configs = get_slot_configs()
        prize_info = None
        for config in slot_configs:
            if config[1] == combination:  # config[1] = combination
                prize_info = config
                break

        if not prize_info:
            await callback.answer("❌ Неизвестная комбинация")
            return

        prize_name = prize_info[6]  # config[6] = name

        # Форматируем награду
        if reward_type == "money":
            reward_text = f"{reward_amount}₽"
        elif reward_type == "stars":
            reward_text = f"{reward_amount}⭐️"
        elif reward_type == "ton":
            reward_text = f"{reward_amount} TON"
        else:
            reward_text = str(reward_amount)

        # Обновляем статус выигрыша с дополнительными данными
        from app.database.models import update_slot_win_status_with_extra, add_stars_to_user, add_ton_to_user
        extra_data = json.dumps({
            "confirmed_at": confirm_time,
            "confirmed_by": admin_username
        })
        update_slot_win_status_with_extra(win_id, "completed", extra_data)

        # Начисляем награду пользователю
        user_tg_id = win_data['tg_id']
        if reward_type == "stars":
            add_stars_to_user(user_tg_id, reward_amount)
        elif reward_type == "ton":
            add_ton_to_user(user_tg_id, reward_amount)
        # Деньги не начисляем здесь, так как они начисляются автоматически

        # Уведомляем пользователя о подтверждении выигрыша
        try:
            message_text = f"✅ Ваш выигрыш отправлен!\nВремя подтверждения: {confirm_time}"
            await callback.bot.send_message(user_tg_id, message_text)

        except Exception as e:
            logging.error(f"Ошибка уведомления пользователя: {e}")

        # Обновляем сообщение администратора
        try:
            new_text = (
                f"\n\n✅ ВЫИГРЫШ #{win_id} ОТПРАВЛЕН\n"
                f"Время подтверждения: {confirm_time}\n"
                f"Администратор: {admin_username}"
            )

            if callback.message.text:
                await callback.message.edit_text(
                    text=callback.message.text + new_text,
                    reply_markup=None,  # Убираем кнопки после подтверждения
                    parse_mode="HTML"
                )
            else:
                await callback.message.answer(new_text)

        except Exception as e:
            logging.error(f"Ошибка обновления сообщения: {e}")

        await callback.answer("✅ Выигрыш отправлен!")

    except Exception as e:
        logging.error(f"[SLOT] Ошибка подтверждения {win_id}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при подтверждении")

@router.callback_query(F.data.startswith("slot_win_reject_"))
async def slot_win_reject_handler(callback: types.CallbackQuery):
    """Отклонение выигрыша слот-машины"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    win_id = int(callback.data.replace("slot_win_reject_", ""))
    
    try:
        win_data = get_slot_win_by_id(win_id)
        if not win_data or len(win_data) < 7:
            await callback.answer("❌ Ошибка данных выигрыша")
            return
        
        # Безопасное извлечение данных
        win_id = win_data[0]
        user_id = win_data[1]
        combination = win_data[2]
        reward_type = win_data[3]
        reward_amount = win_data[4]
        created_at = win_data[6] if len(win_data) > 6 else datetime.datetime.now().strftime('%d.%m.%Y %H:%M')

        # Обновляем статус выигрыша
        update_slot_win_status(win_id, "rejected", callback.message.message_id)

        # Пытаемся уведомить пользователя (если чат доступен)
        try:
            await callback.bot.send_message(
                user_id,
                f"❌ <b>Ваш выигрыш отклонен</b>\n\n"
                f"🏆 Комбинация: {combination}\n"
                f"💰 Награда: {reward_amount} "
                f"{'⭐️' if reward_type == 'stars' else 'TON' if reward_type == 'ton' else '₽'}\n\n"
                f"💬 Обратитесь в поддержку для уточнения",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.warning(f"[SLOT] Не удалось уведомить пользователя {user_id}: {e}")

        await callback.answer("❌ Выигрыш отклонен!")

        # Обновляем сообщение админу
        text = (
            f"❌ ВЫИГРЫШ ОТКЛОНЕН\n\n"
            f"🔧 ID: {win_id}\n"
            f"👤 ID пользователя: {user_id}\n"
            f"🎰 Комбинация: {combination}\n"
            f"💰 Награда: {reward_amount} "
            f"{'⭐️' if reward_type == 'stars' else 'TON' if reward_type == 'ton' else '₽'}\n"
            f"🕒 Время: {created_at}"
        )
        
        await callback.message.edit_text(text, parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"[SLOT] Ошибка отклонения выигрыша {win_id}: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)[:50]}...")

@router.callback_query(F.data.startswith("slot_win_delete_"))
async def slot_win_delete_handler(callback: types.CallbackQuery):
    """Удаление выигрыша слот-машины"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    win_id = int(callback.data.replace("slot_win_delete_", ""))
    
    try:
        # Удаляем выигрыш
        from app.database.models import delete_slot_win
        delete_slot_win(win_id)
        
        await callback.answer("🗑️ Выигрыш удален!")
        
        # Возвращаемся к списку выигрышей
        await admin_slot_wins_handler(callback)
        
    except Exception as e:
        logging.error(f"[SLOT] Ошибка удаления выигрыша {win_id}: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}")

@router.callback_query(F.data == "claim_referral_bonus")
async def claim_referral_bonus_handler(callback: types.CallbackQuery):
    """Активация реферальных бонусов"""
    await callback.answer()

    try:
        from app.database.models import get_unclaimed_referrals_count, claim_referral_bonus, get_user_profile

        user = get_user_profile(callback.from_user.id)
        if not user:
            await callback.message.answer("❌ Пользователь не найден")
            return

        user_id = user['id']

        # Проверяем количество неактивированных рефералов
        unclaimed_count = await get_unclaimed_referrals_count(user_id)

        if unclaimed_count == 0:
            await callback.message.answer(
                "🎁 <b>Реферальные бонусы</b>\n\n"
                "❌ У вас нет неактивированных рефералов.\n\n"
                "💡 Приглашайте друзей по вашей реферальной ссылке, "
                "и после их регистрации вы сможете получить бонусные попытки!",
                parse_mode="HTML"
            )
            return

        # Активируем все неактивированные бонусы
        success, activated_count, total_attempts = await claim_referral_bonus(user_id)

        if success:
            await callback.message.answer(
                f"🎉 <b>Реферальные бонусы активированы!</b>\n\n"
                f"👥 Активировано рефералов: <b>{activated_count}</b>\n"
                f"🎰 Получено попыток: <b>{total_attempts}</b>\n\n"
                f"Попытки добавлены к вашему счету в слот-машине!",
                parse_mode="HTML"
            )

            # Уведомляем админов
            from app.utils.misc import notify_admins
            await notify_admins(
                callback.bot,
                f"🎁 <b>Активация реферальных бонусов</b>\n\n"
                f"👤 Пользователь: @{callback.from_user.username or 'Unknown'} (ID: {callback.from_user.id})\n"
                f"👥 Активировано рефералов: {activated_count}\n"
                f"🎰 Начислено попыток: {total_attempts}",
                parse_mode="HTML"
            )
        else:
            await callback.message.answer(
                "❌ <b>Ошибка активации</b>\n\n"
                "Не удалось активировать реферальные бонусы. "
                "Попробуйте позже или обратитесь в поддержку.",
                parse_mode="HTML"
            )

    except Exception as e:
        logging.error(f"[REFERRAL] Ошибка активации бонусов: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка при активации бонусов. Попробуйте позже.",
            parse_mode="HTML"
        )

# Админские обработчики для слот-машины
@router.callback_query(F.data == "admin_slot_wins")
async def admin_slot_wins_handler(callback: types.CallbackQuery):
    """Админский просмотр выигрышей слот-машины"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return

    try:
        wins = await get_slot_wins_async(status="pending")

        if not wins:
            text = "📋 ВЫИГРЫШИ СЛОТ-МАШИНЫ\n\nНет новых выигрышей"
        else:
            text = "📋 ВЫИГРЫШИ СЛОТ-МАШИНЫ\n\n"
            for win in wins[:10]:  # Показываем первые 10
                try:
                    # Безопасное получение данных с проверкой длины
                    if len(win) < 9:
                        logging.warning(f"Неполные данные выигрыша: {win}")
                        continue

                    win_id = win[0] if len(win) > 0 else 0          # sm.id
                    user_id = win[1] if len(win) > 1 else 0         # sm.user_id
                    tg_id = win[2] if len(win) > 2 else 0           # u.tg_id
                    full_name = win[3] if len(win) > 3 else "Unknown"       # u.full_name
                    combination = win[4] if len(win) > 4 else "???"     # sm.combination
                    reward_type = win[5] if len(win) > 5 else "unknown"     # sm.reward_type
                    reward_amount = win[6] if len(win) > 6 else 0   # sm.reward_amount
                    created_at = win[8] if len(win) > 8 else "Unknown"      # sm.created_at

                    user_profile = get_user_profile(tg_id)
                    username = user_profile['username'] if user_profile and user_profile.get('username') else f"ID {tg_id}"

                    if reward_type == "money":
                        reward_text = f"{reward_amount}₽"
                    elif reward_type == "stars":
                        reward_text = f"{reward_amount}⭐"
                    elif reward_type == "ton":
                        reward_text = f"{reward_amount} TON"
                    else:
                        reward_text = f"{reward_amount}"

                    text += f"👤 {username}\n"
                    text += f"🎰 {combination} → {reward_text}\n"
                    text += f"📅 {created_at[:10] if isinstance(created_at, str) and len(created_at) >= 10 else str(created_at)}\n"
                    text += f"🔧 ID: {win_id}\n\n"

                except Exception as e:
                    logging.error(f"Ошибка обработки выигрыша {win}: {e}")
                    continue

        await callback.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]]
        ))

    except Exception as e:
        logging.error(f"Error in admin_slot_wins_handler: {str(e)}", exc_info=True)
        await callback.answer("⚠️ Произошла ошибка при загрузке выигрышей. Попробуйте позже.", show_alert=True)


# Добавляем новые обработчики после существующих в router

@router.callback_query(F.data == "slot_prizes")
async def slot_prizes_handler(callback: types.CallbackQuery):
    """Показывает список наград слот-машины из базы данных"""
    user_id = callback.from_user.id
    is_user_admin = is_admin(user_id)

    if is_user_admin:
        text = (
            "🏆 <b>Список наград слот-машины (Админ)</b> 🏆\n\n"
            "🎰 Возможные выигрышные комбинации:\n\n"
        )
    else:
        text = (
            "🏆 <b>Список наград слот-машины</b> 🏆\n\n"
            "🎰 Возможные выигрышные комбинации:\n\n"
        )

    # Получаем конфигурации из базы данных
    slot_configs = get_slot_configs()

    # Добавляем информацию о каждой выигрышной комбинации из БД
    for config in slot_configs:
        config_id, combination, reward_type, reward_amount, chance_percent, emoji, name = config

        # Форматируем награду
        if reward_type == "money":
            reward_text = f"{int(reward_amount)}₽"
        elif reward_type == "stars":
            reward_text = f"{int(reward_amount)}⭐️"
        elif reward_type == "ton":
            reward_text = f"{reward_amount} TON"
        else:
            reward_text = str(reward_amount)

        # ВАЖНО: Показываем проценты ТОЛЬКО админам, обычные пользователи их не видят
        if is_user_admin:
            text += (
                f"{combination} - {name}\n"
                f"💰 Награда: {reward_text}\n"
                f"🎯 Шанс: {chance_percent}%\n\n"
            )
        else:
            # Обычные пользователи НЕ видят проценты выпадения
            text += (
                f"{combination} - {name}\n"
                f"💰 Награда: {reward_text}\n\n"
            )

    text += "💎 Крутите слоты и выигрывайте призы!"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Крутить слоты", callback_data="spin_slot")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="slot_machine")]
    ])

    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

async def slot_machine_menu_no_delete(callback: types.CallbackQuery):
    """Главное меню слот-машины БЕЗ удаления предыдущего сообщения (для рассылки)"""
    try:
        user_id = callback.from_user.id

        # 1. Проверка черного списка
        from app.handlers.user import check_blacklist_and_respond
        if await check_blacklist_and_respond(user_id, callback):
            return

        # 2. Проверка подписки (обязательная для слот-машинки)
        if not await check_subscription(user_id, callback.bot):
            await show_subscription_message(callback, callback.bot)
            return

        # 3. Получаем профиль пользователя
        user_profile = get_user_profile(user_id)
        if not user_profile:
            await callback.answer("❌ Профиль не найден", show_alert=True)
            return

        # 4. Проверяем, нужно ли сбросить попытки
        if should_reset_daily_attempts(user_id):
            reset_slot_spins(user_id)

        # 5. Получаем статистику пользователя
        spins_used, last_reset = get_user_slot_spins(user_id)
        daily_attempts = int(get_admin_setting('slot_daily_attempts', '5'))

        # 6. Получаем количество неактивированных рефералов
        from app.database.models import get_unclaimed_referrals_count
        try:
            unclaimed_referrals = await get_unclaimed_referrals_count(user_profile['id'])
        except Exception as e:
            logging.error(f"Ошибка получения неактивированных рефералов: {e}")
            unclaimed_referrals = 0

        # 7. Формируем текст с попытками
        from app.utils.slot_machine import format_attempts_text
        attempts_text = format_attempts_text(spins_used, daily_attempts)

        # 8. Формируем основной текст
        slot_description = get_admin_setting('slot_description',
            'Слот-машина — это бесплатная игра от Legal Stars. 🎰🎁 Выигрывайте деньги, звёзды и TON!')

        text = (
            f"🎰 <b>Слот-машина Legal Stars</b> 🎰\n\n"
            f"{slot_description}\n\n"
            f"🔄 <b>Попытки сбрасываются каждый день в 00:00 МСК</b>\n"
            f"{attempts_text}"
        )

        # 9. Создаем клавиатуру
        referral_button_text = f"🎁 Получить бонус ({unclaimed_referrals})" if unclaimed_referrals > 0 else "🎁 Получить бонус"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎰 Крутить слоты", callback_data="spin_slot")],
            [InlineKeyboardButton(text=referral_button_text, callback_data="claim_referral_bonus")],
            [InlineKeyboardButton(text="🏆 Список наград", callback_data="slot_prizes")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="slot_stats")],
            [InlineKeyboardButton(text="🎁 Мои призы", callback_data="my_prizes")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
        ])

        # 10. НЕ удаляем предыдущее сообщение, просто отправляем новое
        slot_photo = get_admin_setting('slot_photo', 'https://imgur.com/a/TkOPe7c.jpeg')
        await callback.message.answer_photo(
            photo=slot_photo,
            caption=text,
            reply_markup=kb,
            parse_mode="HTML"
        )

    except Exception as e:
        logging.error(f"Ошибка в slot_machine_menu_no_delete: {e}")
        await callback.answer("⚠️ Произошла ошибка. Попробуйте позже.", show_alert=True)

@router.callback_query(F.data == "slot_stats")
async def slot_stats_handler(callback: types.CallbackQuery):
    """Статистика пользователя из базы данных"""
    try:
        user_id = callback.from_user.id

        # Получаем все выигрыши пользователя из БД
        user_wins = await get_slot_wins_async(user_id=user_id)  # Получаем выигрыши пользователя

        # Считаем статистику
        total_spins = len(user_wins)  # Общее количество вращений (включая проигрыши)
        winning_spins = len([win for win in user_wins if win[7] in (True, 1)])  # win[7] = is_win

        # Находим самый крупный выигрыш
        biggest_win = 0
        biggest_win_type = ""
        for win in user_wins:
            if win[7] in (True, 1):  # Если выигрыш (sm.is_win)
                reward_amount = win[6]  # sm.reward_amount
                reward_type = win[5]    # sm.reward_type

                # Конвертируем в условные единицы для сравнения
                if reward_type == "money":
                    value = reward_amount
                elif reward_type == "stars":
                    value = reward_amount * 2  # Условно звезды дороже
                elif reward_type == "ton":
                    value = reward_amount * 1000  # TON самый дорогой
                else:
                    value = 0

                if value > biggest_win:
                    biggest_win = value
                    if reward_type == "money":
                        biggest_win_type = f"{int(reward_amount)}₽"
                    elif reward_type == "stars":
                        biggest_win_type = f"{int(reward_amount)}⭐️"
                    elif reward_type == "ton":
                        biggest_win_type = f"{reward_amount} TON"

        win_rate = (winning_spins / total_spins * 100) if total_spins > 0 else 0

        text = (
            "📊 <b>Ваша статистика в слотах</b>\n\n"
            f"🎰 Всего вращений: {total_spins}\n"
            f"🏆 Выигрышных вращений: {winning_spins}\n"
            f"📈 Процент выигрышей: {win_rate:.1f}%\n"
            f"💰 Самый крупный выигрыш: {biggest_win_type if biggest_win_type else 'Нет выигрышей'}\n\n"
            f"🍀 Удачи в следующих играх!"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎰 Крутить слоты", callback_data="spin_slot")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="slot_machine")]
        ])

        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            # Если не удалось отредактировать, отправляем новое сообщение
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка в slot_stats_handler: {e}")
        await callback.answer("⚠️ Ошибка получения статистики.", show_alert=True)