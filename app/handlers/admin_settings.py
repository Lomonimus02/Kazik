"""
Обработчики админских настроек
"""
import re
import json
import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.config import ADMINS
from app.database.models import (
    get_admin_setting, update_admin_setting, get_all_admin_settings,
    get_slot_configs, add_slot_config, delete_slot_config,
    get_activity_rewards, add_activity_reward, delete_activity_reward,
    get_all_users, update_user_referral_percent, get_user_referral_percent,
    get_user_profile_by_id, get_user_profile, get_user_by_username,
    update_user_referral_percent_by_username,
    delete_user_everywhere_full
)
from app.keyboards.main import (
    admin_settings_kb, admin_ui_settings_kb, admin_price_settings_kb,
    admin_stars_settings_kb, admin_slot_settings_kb, admin_activity_settings_kb
)

router = Router()

class AdminSettingStates(StatesGroup):
    waiting_for_value = State()
    waiting_for_slot_combination = State()
    waiting_for_slot_reward = State()
    waiting_for_slot_amount = State()
    waiting_for_slot_chance = State()
    waiting_for_slot_emoji = State()
    waiting_for_user_to_delete = State()
    waiting_for_slot_name = State()
    waiting_for_activity_days = State()
    waiting_for_activity_reward = State()
    waiting_for_activity_amount = State()
    waiting_for_activity_description = State()
    waiting_for_user_id = State()
    waiting_for_referral_username = State()
    waiting_for_referral_percent = State()
    waiting_for_ticket_username = State()
    waiting_for_ticket_amount = State()

class SlotAttemptsStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_attempts = State()

class AdminUIButtonStates(StatesGroup):
    waiting_for_btn_text = State()
    waiting_for_btn_action = State()
    waiting_for_btn_edit_index = State()
    editing_button = State()

class AdminSettings(StatesGroup):
    waiting_for_main_photo = State()

class AdminButtons(StatesGroup):
    waiting_for_button_type = State()
    waiting_for_button_text = State()
    waiting_for_button_action = State()
    editing_button = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

def get_setting_with_default(key: str, default: str = ""):
    value = get_admin_setting(key, "")
    if not value:
        return default
    return value
    
@router.callback_query(F.data == "admin_ui_btn_settings")
async def admin_ui_btn_settings_menu(callback: types.CallbackQuery):
    """Меню настроек кнопок"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return

    try:
        btns = get_admin_setting('main_menu_btns', '[]')
        buttons = json.loads(btns) if btns else []
        
        kb = []
        for i, btn in enumerate(buttons):
            btn_text = btn.get('text', 'Без текста')[:15]
            kb.append([
                InlineKeyboardButton(text=f"✏️ {btn_text}", callback_data=f"admin_ui_btn_edit_{i}"),
                InlineKeyboardButton(text="🗑", callback_data=f"admin_ui_btn_remove_{i}")
            ])
        
        kb.append([InlineKeyboardButton(text="➕ Добавить кнопку", callback_data="admin_ui_btn_add")])
        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_ui_settings")])
        
        await callback.message.edit_text(
            "⚙️ <b>Настройки кнопок</b>\n\nТекущие кнопки:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error in btn settings menu: {e}")
        await callback.answer("❌ Ошибка загрузки кнопок")
        return
 
             
        
@router.callback_query(F.data == "admin_ui_btn_add")
async def admin_ui_btn_add(callback: types.CallbackQuery, state: FSMContext):
    """Добавление новой кнопки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    await state.set_state(AdminUIButtonStates.waiting_for_btn_text)
    await callback.message.edit_text(
        "✏️ Введите текст новой кнопки (макс. 30 символов):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_ui_btn_settings")]]
        )
    )

@router.message(AdminUIButtonStates.waiting_for_btn_text)
async def process_btn_text(message: types.Message, state: FSMContext):
    """Обработка текста кнопки"""
    if not is_admin(message.from_user.id):
        return
    
    btn_text = message.text.strip()
    if not btn_text or len(btn_text) > 30:
        await message.answer("❌ Текст должен быть от 1 до 30 символов. Попробуйте еще раз:")
        return
    
    await state.update_data(btn_text=btn_text)
    await state.set_state(AdminUIButtonStates.waiting_for_btn_action)
    
    await message.answer(
        "🔘 Выберите тип действия для кнопки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Callback", callback_data="ui_btn_type_callback"),
                InlineKeyboardButton(text="URL", callback_data="ui_btn_type_url")
            ],
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_ui_btn_settings")]
        ])
    )

@router.callback_query(F.data.startswith("ui_btn_type_"))
async def set_ui_btn_type(callback: types.CallbackQuery, state: FSMContext):
    """Установка типа кнопки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    btn_type = callback.data.split("_")[-1]
    await state.update_data(btn_type=btn_type)
    
    prompt = {
        'callback': "✏️ Введите callback_data (латинские буквы, цифры и _):",
        'url': "✏️ Введите URL (начинается с http:// или https://):"
    }[btn_type]
    
    await callback.message.edit_text(
        prompt,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_ui_btn_settings")]]
        )
    )

@router.message(AdminUIButtonStates.waiting_for_btn_action)
async def process_btn_action(message: types.Message, state: FSMContext):
    """Обработка действия кнопки"""
    if not is_admin(message.from_user.id):
        return
    
    action = message.text.strip()
    data = await state.get_data()
    btn_type = data.get('btn_type')
    
    # Валидация
    if btn_type == 'callback' and not re.match(r'^[a-zA-Z0-9_]+$', action):
        await message.answer("❌ Используйте только латинские буквы, цифры и _. Попробуйте еще раз:")
        return
    elif btn_type == 'url' and not action.startswith(('http://', 'https://')):
        await message.answer("❌ URL должен начинаться с http:// или https://. Попробуйте еще раз:")
        return
    
    # Получаем текущие кнопки
    btns = json.loads(get_admin_setting('main_menu_btns', '[]'))
    
    # Создаем новую кнопку
    new_btn = {'text': data['btn_text']}
    if btn_type == 'callback':
        new_btn['callback_data'] = action
    else:
        new_btn['url'] = action
    
    # Добавляем кнопку
    btns.append(new_btn)
    
    # Сохраняем
    update_admin_setting('main_menu_btns', json.dumps(btns, ensure_ascii=False))
    
    await message.answer("✅ Новая кнопка успешно добавлена!")
    await state.clear()
    await admin_ui_btn_settings_menu(message)

@router.callback_query(F.data.startswith("admin_ui_btn_edit_"))
async def admin_ui_btn_edit(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование кнопки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    try:
        idx = int(callback.data.split("_")[-1])
        btns = json.loads(get_admin_setting('main_menu_btns', '[]'))
        
        if idx >= len(btns):
            await callback.answer("❌ Кнопка не найдена")
            return
            
        await state.update_data(edit_index=idx)
        await state.set_state(AdminUIButtonStates.waiting_for_btn_edit_index)
        
        btn = btns[idx]
        await callback.message.edit_text(
            f"✏️ Редактирование кнопки #{idx + 1}\n\n"
            f"Текущий текст: <code>{btn.get('text', '')}</code>\n"
            f"Тип: <b>{'URL' if 'url' in btn else 'Callback'}</b>\n"
            f"Действие: <code>{btn.get('url', btn.get('callback_data', ''))}</code>\n\n"
            "Введите новый текст кнопки:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_ui_btn_settings")]]
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error editing button: {e}")
        await callback.answer("❌ Ошибка при редактировании кнопки")

@router.message(AdminUIButtonStates.waiting_for_btn_edit_index)
async def process_btn_edit_text(message: types.Message, state: FSMContext):
    """Обработка нового текста при редактировании"""
    if not is_admin(message.from_user.id):
        return
    
    new_text = message.text.strip()
    if not new_text or len(new_text) > 30:
        await message.answer("❌ Текст должен быть от 1 до 30 символов. Попробуйте еще раз:")
        return
    
    data = await state.get_data()
    idx = data.get('edit_index')
    btns = json.loads(get_admin_setting('main_menu_btns', '[]'))
    
    if idx < len(btns):
        btns[idx]['text'] = new_text
        update_admin_setting('main_menu_btns', json.dumps(btns, ensure_ascii=False))
        await message.answer("✅ Текст кнопки успешно обновлен!")
    
    await state.clear()
    await admin_ui_btn_settings_menu(message)

@router.callback_query(F.data.startswith("admin_ui_btn_remove_"))
async def admin_ui_btn_remove(callback: types.CallbackQuery):
    """Удаление кнопки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    try:
        idx = int(callback.data.split("_")[-1])
        btns = json.loads(get_admin_setting('main_menu_btns', '[]'))
        
        if idx < len(btns):
            deleted_text = btns[idx].get('text', '')
            btns.pop(idx)
            update_admin_setting('main_menu_btns', json.dumps(btns, ensure_ascii=False))
            await callback.answer(f"🗑 Кнопка '{deleted_text}' удалена")
        
        await admin_ui_btn_settings_menu(callback)
    except Exception as e:
        logging.error(f"Error removing button: {e}")
        await callback.answer("❌ Ошибка при удалении кнопки")

@router.callback_query(F.data == "admin_slot_attempts")
async def admin_slot_attempts(callback: types.CallbackQuery):
    """Перенаправляет на статистику попыток слот-машины"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    # Перенаправляем на статистику
    await admin_slot_attempts_stats(callback)

@router.callback_query(F.data == "admin_slot_attempts_stats")
async def admin_slot_attempts_stats(callback: types.CallbackQuery):
    """Статистика по попыткам слот-машины"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    import aiosqlite
    from datetime import datetime
    
    try:
        async with aiosqlite.connect('data/users.db') as db:
            # Получаем топ пользователей по отрицательным попыткам (бонусные попытки)
            cursor = await db.execute("""
                SELECT u.tg_id, u.username, ra.attempts_used 
                FROM roulette_attempts ra
                JOIN users u ON ra.user_id = u.tg_id
                WHERE ra.attempts_used < 0
                ORDER BY ra.attempts_used ASC
                LIMIT 20
            """)
            bonus_users = await cursor.fetchall()
            
            # Получаем общую статистику
            cursor = await db.execute("SELECT COUNT(*) FROM roulette_attempts")
            total_users = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT SUM(attempts_used) FROM roulette_attempts WHERE attempts_used < 0")
            total_bonus = abs((await cursor.fetchone())[0] or 0)
            
            cursor = await db.execute("SELECT COUNT(*) FROM roulette_attempts WHERE attempts_used > 0")
            active_users = (await cursor.fetchone())[0]
    
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")
        return
    
    text = f"📊 <b>Статистика попыток слот-машины</b>\n\n"
    text += f"👥 Всего пользователей: {total_users}\n"
    text += f"🎯 Активных сегодня: {active_users}\n"
    text += f"🎁 Всего бонусных попыток: {total_bonus}\n\n"
    text += "🏆 <b>Топ пользователей с бонусными попытками:</b>\n"
    
    for i, user in enumerate(bonus_users[:10], 1):
        tg_id, username, attempts = user
        text += f"{i}. @{username if username else 'N/A'} (ID: {tg_id}): {abs(attempts)} попыток\n"
    
    keyboard = [
        [types.InlineKeyboardButton(text="➕ Добавить попытки", callback_data="admin_add_slot_attempts")],
        [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_slot_attempts_stats")],
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_slot_settings")]
    ]
    
    await callback.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@router.callback_query(F.data == "admin_settings")
async def admin_settings_menu(callback: types.CallbackQuery):
    """Админ-меню настроек"""
    if not (callback and getattr(callback, 'from_user', None) and hasattr(callback.from_user, 'id') and is_admin(callback.from_user.id)):
        if callback:
            await callback.answer("Доступ запрещён", show_alert=True)
        return
    if getattr(callback, 'message', None):
        await callback.message.answer(
            "⚙️ <b>Админ-панель настроек</b>\n\n"
            "Выберите раздел для настройки:",
            reply_markup=admin_settings_kb(),
            parse_mode="HTML"
        )

@router.callback_query(F.data == "admin_ui_settings")
async def admin_ui_settings_menu(callback: types.CallbackQuery):
    """Настройки интерфейса"""
    if not (callback and getattr(callback, 'from_user', None) and hasattr(callback.from_user, 'id') and is_admin(callback.from_user.id)):
        if callback:
            await callback.answer("Доступ запрещён", show_alert=True)
        return
    if getattr(callback, 'message', None):
        await callback.message.answer(
            "🎨 <b>Настройки интерфейса</b>\n\n"
            "Настройте внешний вид бота:",
            reply_markup=admin_ui_settings_kb(),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("admin_setting_"))
async def admin_setting_handler(callback: types.CallbackQuery, state: FSMContext):
    if not (callback.from_user and isinstance(callback.from_user.id, int) and is_admin(callback.from_user.id)):
        if callback:
            await callback.answer("❌ Доступ запрещен")
        return
    if not (callback and getattr(callback, 'data', None)):
        if callback:
            await callback.answer("Ошибка: пустой callback_data")
        return
    raw_key = callback.data.replace("admin_setting_", "") if callback.data else ""
    key_map = {
        'prem_3': 'prem_3_price',
        'prem_6': 'prem_6_price',
        'prem_12': 'prem_12_price',
        'stars_rate_low': 'stars_rate_low',
        'stars_rate_high': 'stars_rate_high',
        'stars_threshold': 'stars_threshold',
        'slot_daily_attempts': 'slot_daily_attempts',
        'slot_reset_hour': 'slot_reset_hour',
        'withdrawal_commission': 'withdrawal_commission',
    }
    setting_key = key_map.get(raw_key, raw_key)
    # Для описаний и фото подставляем дефолт
    default_map = {
        'stars_description': '⭐️ Покупка Telegram Stars — выберите количество звёзд и способ оплаты:',
        'premium_description': '💎 Telegram Premium — это официальная подписка от Telegram, дающая дополнительные возможности. Выберите желаемый срок подписки:',
        'crypto_description': '💎 Покупка криптовалюты — выберите монету и способ оплаты:',
        'reviews_description': '🌟 Отзывы наших клиентов 🌟\nМы ценим ваше мнение и стремимся сделать наш сервис лучше с каждым днем! Здесь вы можете ознакомиться с отзывами наших клиентов,',
        'about_description': 'ℹ️ О проекте Legal Stars — легальная покупка Telegram Stars, Premium и криптовалюты. Безопасно, быстро, удобно!',
        'main_description': 'Добро пожаловать!\n\nВыберите нужный раздел ниже:',
        'main_title': 'Legal Stars — легальная покупка Telegram Stars, Premium и криптовалюты.',
        'stars_photo': 'https://imgur.com/a/TkOPe7c.jpeg',
        'premium_photo': 'https://imgur.com/a/TkOPe7c.jpeg',
        'crypto_photo': 'https://imgur.com/a/TkOPe7c.jpeg',
        'reviews_photo': 'https://imgur.com/a/TkOPe7c.jpeg',
        'about_photo': 'https://imgur.com/a/TkOPe7c.jpeg',
        'support_description': '📞 <b>Техническая поддержка</b>\n\nЕсли у вас есть вопросы или проблемы, создайте тикет поддержки.\n\nНаши специалисты ответят вам в ближайшее время.',
        'support_photo': 'https://imgur.com/a/TkOPe7c.jpeg',
        'profile_description': '🚀 <b>Ваш профиль</b>\n\nЗдесь вы можете посмотреть информацию о своем аккаунте, балансе и истории операций.',
        'profile_photo': 'https://imgur.com/a/TkOPe7c.jpeg',
        'slot_description': '🎰 <b>Слот-машина</b>\n\nСлот-машина — это бесплатная игра от Legal Stars.\n\n🎁Выигрывайте деньги, звёзды и TON!',
        'slot_photo': 'https://imgur.com/a/TkOPe7c.jpeg',
        'calendar_description': '📅 <b>Календарь активности</b>\n\nОтмечайте активность каждый день и получайте награды за постоянство!',
        'calendar_photo': 'https://imgur.com/a/TkOPe7c.jpeg',
    }
    current_value = get_setting_with_default(setting_key, default_map.get(setting_key, ""))
    if setting_key.startswith("prem_") or setting_key == "withdrawal_commission":
        prev_menu = "admin_price_settings"
    elif setting_key.startswith("stars_rate") or setting_key == "stars_threshold":
        prev_menu = "admin_stars_settings"
    elif setting_key.startswith("slot_"):
        prev_menu = "admin_slot_settings"
    elif setting_key.startswith("activity_"):
        prev_menu = "admin_activity_settings"
    elif setting_key.endswith("_photo"):
        prev_menu = "admin_ui_photo_settings"
    elif setting_key.endswith("_description") or setting_key.endswith("_title"):
        prev_menu = "admin_ui_titles_settings"
    else:
        prev_menu = "admin_settings"
    await state.update_data(setting_key=setting_key)
    await state.update_data(prev_menu=prev_menu)
    await state.set_state(AdminSettingStates.waiting_for_value)
    text = f"📝 <b>Изменение настройки</b>\n\n"
    text += f"Ключ: <code>{setting_key}</code>\n"
    text += f"Текущее значение: <code>{current_value}</code>\n\n"
    text += "Отправьте новое значение:"
    if getattr(callback, 'message', None):
        await callback.message.answer(text, reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data=prev_menu)]]
        ), parse_mode="HTML")

@router.message(AdminSettingStates.waiting_for_value)
async def process_setting_value(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    setting_key = data.get('setting_key')
    prev_menu = data.get('prev_menu', 'admin_settings')
    
    # Обработка фото - улучшенная версия
    if setting_key.endswith('_photo'):
        if message.photo:
            # Для фото берем file_id самого большого размера
            value = message.photo[-1].file_id
        elif message.text and (message.text.startswith('http://') or message.text.startswith('https://')):
            # Если это URL, сохраняем как есть
            value = message.text
        else:
            await message.answer("❌ Отправьте фото или корректную URL-ссылку")
            return
        
        update_admin_setting(setting_key, value)
        await message.answer(f"✅ Фото для {setting_key} обновлено!")
        await state.clear()
        
        # Возвращаем в соответствующее меню
        if prev_menu == "admin_ui_settings":
            # Создаем фиктивный callback для вызова меню
            class FakeCallback:
                def __init__(self, user_id):
                    self.from_user = types.User(id=user_id, is_bot=False, first_name="Admin")
                    self.message = message
            fake_callback = FakeCallback(message.from_user.id)
            await admin_ui_settings_menu(fake_callback)
        elif prev_menu == "admin_ui_photo_settings":
            # Создаем фиктивный callback для вызова меню
            class FakeCallback:
                def __init__(self, user_id):
                    self.from_user = types.User(id=user_id, is_bot=False, first_name="Admin")
                    self.message = message
            fake_callback = FakeCallback(message.from_user.id)
            await admin_ui_photo_settings_menu(fake_callback)
        else:
            await admin_settings_menu(message)
        return
    
    # Остальная обработка значений
    default_map = {
        'stars_description': '⭐️ Покупка Telegram Stars — выберите количество звёзд и способ оплаты:',
        'premium_description': '💎 Telegram Premium — это официальная подписка от Telegram, дающая дополнительные возможности. Выберите желаемый срок подписки:',
        'crypto_description': '💎 Покупка криптовалюты — выберите монету и способ оплаты:',
        'reviews_description': '🌟 Отзывы наших клиентов 🌟\nМы ценим ваше мнение и стремимся сделать наш сервис лучше с каждым днем! Здесь вы можете ознакомиться с отзывами наших клиентов,',
        'about_description': 'ℹ️ О проекте Legal Stars — легальная покупка Telegram Stars, Premium и криптовалюты. Безопасно, быстро, удобно!',
        'profile_description': '🚀 <b>Ваш профиль</b>\n\nЗдесь вы можете посмотреть информацию о своем аккаунте, балансе и истории операций.',
        'slot_description': '🎰 <b>Слот-машина</b>\n\nСлот-машина — это бесплатная игра от Legal Stars.\n\n🎁Выигрывайте деньги, звёзды и TON!',
        'calendar_description': '📅 <b>Календарь активности</b>\n\nОтмечайте активность каждый день и получайте награды за постоянство!'
    }
    value = message.text if message and getattr(message, 'text', None) else ""
    if setting_key in default_map and (not value or not value.strip()):
        value = default_map[setting_key]
    
    # Валидация числовых значений
    if setting_key and (setting_key.startswith('prem_') or setting_key == 'withdrawal_commission' or 'rate' in setting_key or 'threshold' in setting_key):
        try:
            if not message or getattr(message, 'text', None) is None:
                raise ValueError()
            float(message.text)
        except ValueError:
            if message:
                await message.answer("❌ Введите корректное число!")
            return
    
    if setting_key:
        update_admin_setting(setting_key, value)
        if message:
            await message.answer(f"✅ Настройка <b>{setting_key}</b> обновлена на: <code>{value}</code>", parse_mode="HTML")
    
    await state.clear()
    from app.keyboards.main import (
        admin_settings_kb, admin_price_settings_kb, admin_stars_settings_kb, 
        admin_slot_settings_kb, admin_activity_settings_kb
    )
    
    if prev_menu == "admin_settings":
        if message:
            await message.answer("⚙️ <b>Админ-панель настроек</b>\n\nВыберите раздел для настройки:", reply_markup=admin_settings_kb(), parse_mode="HTML")
    elif prev_menu == "admin_price_settings":
        if message:
            await message.answer("💰 <b>Настройки цен</b>\n\nВыберите элемент для изменения:", reply_markup=admin_price_settings_kb(), parse_mode="HTML")
    elif prev_menu == "admin_stars_settings":
        if message:
            await message.answer("⭐ <b>Настройки звезд</b>\n\nВыберите элемент для изменения:", reply_markup=admin_stars_settings_kb(), parse_mode="HTML")
    elif prev_menu == "admin_slot_settings":
        if message:
            await message.answer("🎰 <b>Настройки слот-машины</b>\n\nВыберите действие:", reply_markup=admin_slot_settings_kb(), parse_mode="HTML")
    elif prev_menu == "admin_referral_percents":
        from app.database.models import get_all_users, get_user_referral_percent
        users = get_all_users()
        text = "👥 <b>Реферальные проценты</b>\n\nВыберите пользователя для изменения процента:"
        keyboard = []
        for user in users[:10]:
            percent = get_user_referral_percent(user[1])
            keyboard.append([
                types.InlineKeyboardButton(
                    text=f"{user[2]} ({percent}%)",
                    callback_data=f"ref_user_{user[1]}"
                )
            ])
        keyboard.append([types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_settings")])
        if message:
            await message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    else:
        if message:
            await message.answer("⚙️ <b>Админ-панель настроек</b>\n\nВыберите раздел для настройки:", reply_markup=admin_settings_kb(), parse_mode="HTML")

@router.callback_query(F.data == "admin_price_settings")
async def admin_price_settings_menu(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    text = "💰 <b>Настройки цен</b>\n\nВыберите элемент для изменения:"
    if callback.message:
        await callback.message.answer(text, reply_markup=admin_price_settings_kb(), parse_mode="HTML")

@router.callback_query(F.data.startswith("admin_setting_prem_"))
async def admin_premium_price_handler(callback: types.CallbackQuery, state: FSMContext):
    if not (callback.from_user and is_admin(callback.from_user.id)):
        if callback:
            await callback.answer("❌ Доступ запрещен")
        return
    if not callback.data:
        if callback:
            await callback.answer("Ошибка: пустой callback_data")
        return
    
    # Исправленный маппинг периодов
    period_map = {
        '3': '3_price',
        '6': '6_price',
        '12': '12_price'
    }
    
    period = callback.data.replace("admin_setting_prem_", "")
    setting_key = f"prem_{period_map.get(period, period)}_price"
    
    current_value = get_admin_setting(setting_key, "0")
    await state.update_data(setting_key=setting_key)
    await state.set_state(AdminSettingStates.waiting_for_value)
    
    # Человекочитаемые названия периодов
    period_names = {
        '3': '3 месяца',
        '6': '6 месяцев',
        '12': '12 месяцев'
    }
    
    text = f"💰 <b>Цена Premium {period_names.get(period, period)}</b>\n\n"
    text += f"Текущая цена: <code>{current_value}</code> RUB\n\n"
    text += "Отправьте новую цену (только число):"
    
    if callback.message:
        await callback.message.answer(text, reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_price_settings")]]
        ), parse_mode="HTML")

@router.callback_query(F.data == "admin_setting_withdrawal_commission")
async def admin_withdrawal_commission_handler(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    current_value = get_admin_setting('withdrawal_commission', '3.0')
    await state.update_data(setting_key='withdrawal_commission')
    await state.set_state(AdminSettingStates.waiting_for_value)
    text = f"💸 <b>Комиссия при выводе</b>\n\n"
    text += f"Текущая комиссия: <code>{current_value}</code>%\n\n"
    text += "Отправьте новую комиссию (только число):"
    if callback.message:
        await callback.message.answer(text, reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_price_settings")]]
        ), parse_mode="HTML")

@router.callback_query(F.data == "admin_stars_settings")
async def admin_stars_settings_menu(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    text = "⭐ <b>Настройки звезд</b>\n\nВыберите элемент для изменения:"
    if callback.message:
        await callback.message.answer(text, reply_markup=admin_stars_settings_kb(), parse_mode="HTML")

@router.callback_query(F.data == "admin_slot_settings")
async def admin_slot_settings_menu(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    configs = get_slot_configs()
    daily_attempts = get_admin_setting('slot_daily_attempts', '5')
    text = "🎰 <b>Настройки слот-машины</b>\n\n"
    text += f"Всего комбинаций: {len(configs)}\n"
    text += f"Ежедневных попыток: {daily_attempts}\n\n"
    text += "Выберите действие:"
    keyboard = [
        [types.InlineKeyboardButton(text="➕ Добавить комбинацию", callback_data="slot_add_config")],
        [types.InlineKeyboardButton(text="📋 Список комбинаций", callback_data="slot_list_configs")],
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_settings")]
    ]
    if callback.message:
        await callback.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@router.callback_query(F.data == "slot_add_config")
async def slot_add_config_handler(callback: types.CallbackQuery, state: FSMContext):
    """Начинает процесс добавления новой конфигурации слот-машины"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return

    await state.set_state(AdminSettingStates.waiting_for_slot_combination)
    text = "🎰 <b>Добавление новой комбинации</b>\n\n"
    text += "Отправьте комбинацию символов (например: 🍒🍒🍒):"

    await callback.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_slot_settings")]]
    ), parse_mode="HTML")

@router.message(AdminSettingStates.waiting_for_slot_combination)
async def process_slot_combination(message: types.Message, state: FSMContext):
    if not (message.from_user and hasattr(message.from_user, 'id') and isinstance(message.from_user.id, int) and is_admin(message.from_user.id)):
        return
    if not message.text:
        await message.answer("❌ Введите комбинацию символов!")
        return
    await state.update_data(combination=message.text)
    await state.set_state(AdminSettingStates.waiting_for_slot_reward)
    text = "🎰 <b>Тип награды</b>\n\n"
    text += "Отправьте тип награды:\n"
    text += "• <code>money</code> - деньги (₽)\n"
    text += "• <code>stars</code> - звёзды (⭐️)\n"
    text += "• <code>ton</code> - TON криптовалюта"

    keyboard = [
        [types.InlineKeyboardButton(text="💰 Деньги", callback_data="slot_reward_money")],
        [types.InlineKeyboardButton(text="⭐️ Звёзды", callback_data="slot_reward_stars")],
        [types.InlineKeyboardButton(text="💎 TON", callback_data="slot_reward_ton")],
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_slot_settings")]
    ]

    await message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@router.callback_query(F.data.startswith("slot_reward_"))
async def slot_reward_type_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора типа награды для слот-машины"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return

    reward_type = callback.data.replace("slot_reward_", "")
    await state.update_data(reward_type=reward_type)
    await state.set_state(AdminSettingStates.waiting_for_slot_amount)

    reward_names = {
        "money": "денег (₽)",
        "stars": "звёзд (⭐️)",
        "ton": "TON"
    }

    text = f"🎰 <b>Количество {reward_names.get(reward_type, 'награды')}</b>\n\n"
    text += "Отправьте количество (только число):"

    await callback.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_slot_settings")]]
    ), parse_mode="HTML")

@router.message(AdminSettingStates.waiting_for_slot_reward)
async def process_slot_reward(message: types.Message, state: FSMContext):
    """Обработчик ввода типа награды текстом (для обратной совместимости)"""
    if not (message.from_user and hasattr(message.from_user, 'id') and isinstance(message.from_user.id, int) and is_admin(message.from_user.id)):
        return
    if not message.text:
        await message.answer("❌ Введите тип награды!")
        return
    reward_type = message.text.lower()
    if reward_type not in ['money', 'stars', 'ton']:
        await message.answer("❌ Неверный тип награды. Используйте: money, stars, ton")
        return
    await state.update_data(reward_type=reward_type)
    await state.set_state(AdminSettingStates.waiting_for_slot_amount)

    reward_names = {
        "money": "денег (₽)",
        "stars": "звёзд (⭐️)",
        "ton": "TON"
    }

    text = f"🎰 <b>Количество {reward_names.get(reward_type, 'награды')}</b>\n\n"
    text += "Отправьте количество (только число):"
    await message.answer(text, reply_markup=types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_slot_settings")]]
    ), parse_mode="HTML")

@router.message(AdminSettingStates.waiting_for_slot_amount)
async def process_slot_amount(message: types.Message, state: FSMContext):
    if not (message.from_user and hasattr(message.from_user, 'id') and isinstance(message.from_user.id, int) and is_admin(message.from_user.id)):
        return
    if not message.text:
        await message.answer("❌ Введите число!")
        return
    try:
        amount = float(message.text)
    except Exception:
        await message.answer("❌ Неверное число")
        return
    await state.update_data(amount=amount)
    await state.set_state(AdminSettingStates.waiting_for_slot_chance)
    text = "🎰 <b>Шанс выпадения</b>\n\n"
    text += "Отправьте шанс в процентах (0-100):"
    await message.answer(text, reply_markup=types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_slot_settings")]]
    ), parse_mode="HTML")

@router.message(AdminSettingStates.waiting_for_slot_chance)
async def process_slot_chance(message: types.Message, state: FSMContext):
    if not (message.from_user and hasattr(message.from_user, 'id') and isinstance(message.from_user.id, int) and is_admin(message.from_user.id)):
        return
    if not message.text:
        await message.answer("❌ Введите шанс!")
        return
    try:
        chance = float(message.text)
        if not 0 <= chance <= 100:
            raise ValueError()
    except Exception:
        await message.answer("❌ Неверный шанс. Используйте число от 0 до 100")
        return
    await state.update_data(chance=chance)
    await state.set_state(AdminSettingStates.waiting_for_slot_emoji)
    text = "🎰 <b>Эмодзи комбинации</b>\n\n"
    text += "Отправьте эмодзи для комбинации:"
    await message.answer(text, reply_markup=types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_slot_settings")]]
    ), parse_mode="HTML")

@router.message(AdminSettingStates.waiting_for_slot_emoji)
async def process_slot_emoji(message: types.Message, state: FSMContext):
    if not (message.from_user and hasattr(message.from_user, 'id') and isinstance(message.from_user.id, int) and is_admin(message.from_user.id)):
        return
    if not message.text:
        await message.answer("❌ Введите эмодзи!")
        return
    await state.update_data(emoji=message.text)
    await state.set_state(AdminSettingStates.waiting_for_slot_name)
    text = "🎰 <b>Название комбинации</b>\n\n"
    text += "Отправьте название комбинации:"
    await message.answer(text, reply_markup=types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_slot_settings")]]
    ), parse_mode="HTML")

@router.message(AdminSettingStates.waiting_for_slot_name)
async def process_slot_name(message: types.Message, state: FSMContext):
    if not (message.from_user and hasattr(message.from_user, 'id') and isinstance(message.from_user.id, int) and is_admin(message.from_user.id)):
        return
    if not message.text:
        await message.answer("❌ Введите название комбинации!")
        return
    data = await state.get_data()
    try:
        add_slot_config(
            combination=data['combination'],
            reward_type=data['reward_type'],
            reward_amount=data['amount'],
            chance_percent=data['chance'],
            emoji=data['emoji'],
            name=message.text
        )
        await message.answer(f"✅ Комбинация добавлена:\n\n"
                           f"Комбинация: {data['combination']}\n"
                           f"Тип: {data['reward_type']}\n"
                           f"Количество: {data['amount']}\n"
                           f"Шанс: {data['chance']}%\n"
                           f"Эмодзи: {data['emoji']}\n"
                           f"Название: {message.text}")
    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении: {str(e)}")
    await state.clear()

@router.callback_query(F.data == "slot_list_configs")
async def slot_list_configs(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    configs = get_slot_configs()
    if not configs:
        text = "📋 <b>Комбинации слот-машины</b>\n\nСписок пуст"
    else:
        text = "📋 <b>Комбинации слот-машины</b>\n\n"
        for config in configs:
            text += f"🎰 <b>{config[6]}</b> ({config[1]})\n"
            text += f"   Награда: {config[2]} {config[3]}\n"
            text += f"   Шанс: {config[4]}%\n"
            text += f"   Эмодзи: {config[5]}\n\n"
    keyboard = [[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_slot_settings")]]
    if callback.message:
        await callback.message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@router.callback_query(F.data == "admin_referral_percents")
async def admin_referral_percents_menu(callback: types.CallbackQuery, state: FSMContext):
    if not (callback and getattr(callback, 'from_user', None) and hasattr(callback.from_user, 'id') and is_admin(callback.from_user.id)):
        if callback:
            await callback.answer("❌ Доступ запрещен")
        return

    text = "👥 <b>Управление реферальными процентами</b>\n\n"
    text += "Введите юзернейм пользователя (без @) для изменения реферального процента:"

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_settings")]
    ])

    await state.set_state(AdminSettingStates.waiting_for_referral_username)
    if getattr(callback, 'message', None):
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.message(AdminSettingStates.waiting_for_referral_username)
async def process_referral_username(message: types.Message, state: FSMContext):
    """Обработка ввода юзернейма для изменения реферального процента"""
    if not is_admin(message.from_user.id):
        return

    if not message.text:
        await message.answer("❌ Отправьте текстовое сообщение с юзернеймом")
        return

    username = message.text.strip()
    if not username:
        await message.answer("❌ Введите корректный юзернейм")
        return

    # Ищем пользователя
    user = get_user_by_username(username)
    if not user:
        await message.answer(f"❌ Пользователь с юзернеймом @{username.lstrip('@')} не найден")
        return

    # Сохраняем данные пользователя в состояние
    await state.update_data(
        user_username=user['username'],
        user_tg_id=user['tg_id'],
        user_full_name=user['full_name'],
        current_percent=user['referral_percent']
    )

    # Показываем информацию о пользователе и кнопки управления
    text = f"👥 <b>Управление реферальным процентом</b>\n\n"
    text += f"👤 Пользователь: @{user['username']}\n"
    text += f"📝 Имя: {user['full_name']}\n"
    text += f"📊 Текущий процент: {user['referral_percent']}%\n\n"
    text += "Выберите действие:"

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="⬆️ Повысить %", callback_data="ref_increase_percent"),
            types.InlineKeyboardButton(text="⬇️ Понизить %", callback_data="ref_decrease_percent")
        ],
        [types.InlineKeyboardButton(text="✏️ Установить точное значение", callback_data="ref_set_exact_percent")],
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_referral_percents")]
    ])

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(AdminSettingStates.waiting_for_referral_percent)

@router.callback_query(F.data == "ref_increase_percent")
async def ref_increase_percent(callback: types.CallbackQuery, state: FSMContext):
    """Повышение реферального процента на 1%"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return

    data = await state.get_data()
    username = data.get('user_username')
    current_percent = data.get('current_percent', 5.0)

    new_percent = min(100.0, current_percent + 1.0)  # Максимум 100%

    if update_user_referral_percent_by_username(username, new_percent):
        await state.update_data(current_percent=new_percent)

        text = f"👥 <b>Управление реферальным процентом</b>\n\n"
        text += f"👤 Пользователь: @{username}\n"
        text += f"📊 Новый процент: {new_percent}%\n\n"
        text += "✅ Процент успешно повышен!"

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="⬆️ Повысить %", callback_data="ref_increase_percent"),
                types.InlineKeyboardButton(text="⬇️ Понизить %", callback_data="ref_decrease_percent")
            ],
            [types.InlineKeyboardButton(text="✏️ Установить точное значение", callback_data="ref_set_exact_percent")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_referral_percents")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.answer("❌ Ошибка при обновлении процента")

@router.callback_query(F.data == "ref_decrease_percent")
async def ref_decrease_percent(callback: types.CallbackQuery, state: FSMContext):
    """Понижение реферального процента на 1%"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return

    data = await state.get_data()
    username = data.get('user_username')
    current_percent = data.get('current_percent', 5.0)

    new_percent = max(0.0, current_percent - 1.0)  # Минимум 0%

    if update_user_referral_percent_by_username(username, new_percent):
        await state.update_data(current_percent=new_percent)

        text = f"👥 <b>Управление реферальным процентом</b>\n\n"
        text += f"👤 Пользователь: @{username}\n"
        text += f"📊 Новый процент: {new_percent}%\n\n"
        text += "✅ Процент успешно понижен!"

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="⬆️ Повысить %", callback_data="ref_increase_percent"),
                types.InlineKeyboardButton(text="⬇️ Понизить %", callback_data="ref_decrease_percent")
            ],
            [types.InlineKeyboardButton(text="✏️ Установить точное значение", callback_data="ref_set_exact_percent")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_referral_percents")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.answer("❌ Ошибка при обновлении процента")

@router.callback_query(F.data == "ref_set_exact_percent")
async def ref_set_exact_percent(callback: types.CallbackQuery, state: FSMContext):
    """Установка точного значения процента"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return

    data = await state.get_data()
    username = data.get('user_username')
    current_percent = data.get('current_percent', 5.0)

    text = f"👥 <b>Установка точного процента</b>\n\n"
    text += f"👤 Пользователь: @{username}\n"
    text += f"📊 Текущий процент: {current_percent}%\n\n"
    text += "Введите новый процент (0-100):"

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_referral_percents")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(AdminSettingStates.waiting_for_referral_percent)

@router.message(AdminSettingStates.waiting_for_referral_percent)
async def process_referral_percent(message: types.Message, state: FSMContext):
    """Обработка ввода точного процента"""
    if not is_admin(message.from_user.id):
        return

    if not message.text:
        await message.answer("❌ Отправьте текстовое сообщение с процентом")
        return

    try:
        percent = float(message.text)
        if not 0 <= percent <= 100:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Неверный процент. Используйте число от 0 до 100")
        return

    data = await state.get_data()
    username = data.get('user_username')

    if not username:
        await message.answer("❌ Ошибка: данные пользователя не найдены")
        await state.clear()
        return

    try:
        if update_user_referral_percent_by_username(username, percent):
            await state.update_data(current_percent=percent)

            text = f"👥 <b>Управление реферальным процентом</b>\n\n"
            text += f"👤 Пользователь: @{username}\n"
            text += f"📊 Новый процент: {percent}%\n\n"
            text += "✅ Процент успешно установлен!"

            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="⬆️ Повысить %", callback_data="ref_increase_percent"),
                    types.InlineKeyboardButton(text="⬇️ Понизить %", callback_data="ref_decrease_percent")
                ],
                [types.InlineKeyboardButton(text="✏️ Установить точное значение", callback_data="ref_set_exact_percent")],
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_referral_percents")]
            ])

            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.answer("❌ Ошибка при обновлении процента")
    except Exception as e:
        await message.answer(f"❌ Ошибка при обновлении: {str(e)}")

    # Не очищаем состояние, чтобы можно было продолжить работу с этим пользователем

# === БИЛЕТИКИ СЛОТ-МАШИНЫ ===

@router.callback_query(F.data == "admin_slot_tickets")
async def admin_slot_tickets_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню управления билетиками слот-машины"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return

    text = "🎫 <b>Управление билетиками слот-машины</b>\n\n"
    text += "Здесь вы можете выдать дополнительные попытки для слот-машины пользователям.\n\n"
    text += "Введите юзернейм пользователя (без @):"

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_settings")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(AdminSettingStates.waiting_for_ticket_username)
    await callback.answer()

@router.message(AdminSettingStates.waiting_for_ticket_username)
async def process_ticket_username(message: types.Message, state: FSMContext):
    """Обработка ввода юзернейма для выдачи билетиков"""
    if not is_admin(message.from_user.id):
        return

    if not message.text:
        await message.answer("❌ Отправьте текстовое сообщение с юзернеймом")
        return

    username = message.text.strip().lstrip('@')
    if not username:
        await message.answer("❌ Введите корректный юзернейм")
        return

    # Ищем пользователя
    user = get_user_by_username(username)
    if not user:
        await message.answer(f"❌ Пользователь с юзернеймом @{username} не найден")
        return

    # Сохраняем данные пользователя
    await state.update_data(
        ticket_user_id=user['tg_id'],
        ticket_username=user['username'],
        ticket_full_name=user['full_name']
    )

    text = f"🎫 <b>Выдача билетиков</b>\n\n"
    text += f"👤 Пользователь: @{user['username']}\n"
    text += f"📝 Имя: {user['full_name']}\n\n"
    text += "Введите количество билетиков (попыток) для выдачи:"

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_slot_tickets")]
    ])

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(AdminSettingStates.waiting_for_ticket_amount)

@router.message(AdminSettingStates.waiting_for_ticket_amount)
async def process_ticket_amount(message: types.Message, state: FSMContext):
    """Обработка ввода количества билетиков"""
    if not is_admin(message.from_user.id):
        return

    if not message.text:
        await message.answer("❌ Отправьте текстовое сообщение с количеством")
        return

    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите положительное число")
        return

    data = await state.get_data()
    user_id = data.get('ticket_user_id')
    username = data.get('ticket_username')
    full_name = data.get('ticket_full_name')

    if not user_id:
        await message.answer("❌ Ошибка: данные пользователя не найдены")
        await state.clear()
        return

    try:
        # Добавляем попытки пользователю в таблицу bonus_attempts
        from app.handlers.user import add_slot_attempts
        await add_slot_attempts(user_id, amount)

        # Уведомляем администратора об успехе
        await message.answer(
            f"✅ <b>Билетики успешно выданы!</b>\n\n"
            f"👤 Пользователь: @{username}\n"
            f"📝 Имя: {full_name}\n"
            f"🎫 Выдано попыток: {amount}\n\n"
            f"Пользователь получил уведомление о новых попытках.",
            parse_mode="HTML"
        )

        # Уведомляем пользователя о новых попытках
        try:
            await message.bot.send_message(
                user_id,
                f"🎫 <b>Вам выданы дополнительные попытки!</b>\n\n"
                f"🎰 Количество: {amount} попыток\n"
                f"💫 Теперь вы можете играть в слот-машину дополнительно!\n\n"
                f"Удачи в игре! 🍀",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.warning(f"Не удалось уведомить пользователя {user_id}: {e}")
            await message.answer("⚠️ Билетики выданы, но пользователь не получил уведомление (возможно, заблокировал бота)")

    except Exception as e:
        logging.error(f"Ошибка при выдаче билетиков: {e}")
        await message.answer(f"❌ Ошибка при выдаче билетиков: {str(e)}")

    await state.clear()

    # Возвращаем в меню билетиков
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🎫 Выдать еще билетики", callback_data="admin_slot_tickets")],
        [types.InlineKeyboardButton(text="⬅️ В настройки", callback_data="admin_settings")]
    ])

    await message.answer(
        "🎫 <b>Управление билетиками</b>\n\nВыберите действие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_ui_photo_settings")
async def admin_ui_photo_settings_menu(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    text = "🖼️ <b>Настройки фото</b>\n\nВыберите фото для изменения:"
    await callback.message.answer(text, reply_markup=types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Изменить главное фото", callback_data="admin_setting_main_photo")],
            [types.InlineKeyboardButton(text="Изменить фото Premium", callback_data="admin_setting_premium_photo")],
            [types.InlineKeyboardButton(text="Изменить фото звёзд", callback_data="admin_setting_stars_photo")],
            [types.InlineKeyboardButton(text="Изменить фото отзывов", callback_data="admin_setting_reviews_photo")],
            [types.InlineKeyboardButton(text="Изменить фото криптовалюты", callback_data="admin_setting_crypto_photo")],
            [types.InlineKeyboardButton(text="Изменить фото about", callback_data="admin_setting_about_photo")],
            [types.InlineKeyboardButton(text="Изменить фото поддержки", callback_data="admin_setting_support_photo")],
            [types.InlineKeyboardButton(text="Изменить фото профиля", callback_data="admin_setting_profile_photo")],
            [types.InlineKeyboardButton(text="Изменить фото слот-машины", callback_data="admin_setting_slot_photo")],
            [types.InlineKeyboardButton(text="Изменить фото календаря", callback_data="admin_setting_calendar_photo")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_ui_settings")],
        ]
    ), parse_mode="HTML")

@router.callback_query(F.data == "admin_ui_titles_settings")
async def admin_ui_titles_settings_menu(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    text = "📝 <b>Настройки заголовков и описаний</b>\n\nВыберите элемент для изменения:"
    await callback.message.answer(text, reply_markup=types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Изменить главное описание", callback_data="admin_setting_main_description")],
            [types.InlineKeyboardButton(text="Описание Premium", callback_data="admin_setting_premium_description")],
            [types.InlineKeyboardButton(text="Описание звёзд", callback_data="admin_setting_stars_description")],
            [types.InlineKeyboardButton(text="Описание отзывов", callback_data="admin_setting_reviews_description")],
            [types.InlineKeyboardButton(text="Описание криптовалюты", callback_data="admin_setting_crypto_description")],
            [types.InlineKeyboardButton(text="Описание about", callback_data="admin_setting_about_description")],
            [types.InlineKeyboardButton(text="Описание поддержки", callback_data="admin_setting_support_description")],
            [types.InlineKeyboardButton(text="Описание профиля", callback_data="admin_setting_profile_description")],
            [types.InlineKeyboardButton(text="Описание слот-машины", callback_data="admin_setting_slot_description")],
            [types.InlineKeyboardButton(text="Описание календаря", callback_data="admin_setting_calendar_description")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_ui_settings")],
        ]
    ), parse_mode="HTML")

@router.callback_query(F.data == "admin_ui_btn_settings")
async def admin_ui_btn_settings_menu(callback: types.CallbackQuery):
    """Меню настроек кнопок с проверкой админских прав"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return

    try:
        btns = get_admin_setting('main_menu_btns', '[]')
        buttons = json.loads(btns) if btns else []
        
        kb = []
        for i, btn in enumerate(buttons):
            btn_text = btn.get('text', 'Без текста')[:15]  # Обрезаем длинный текст
            kb.append([
                InlineKeyboardButton(text=f"✏️ {btn_text}", callback_data=f"admin_ui_btn_edit_{i}"),
                InlineKeyboardButton(text="🗑", callback_data=f"admin_ui_btn_remove_{i}")
            ])
        
        kb.append([InlineKeyboardButton(text="➕ Добавить кнопку", callback_data="admin_ui_btn_add")])
        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_ui_settings")])
        
        await callback.message.edit_text(
            "⚙️ <b>Настройки кнопок</b>\n\nТекущие кнопки:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error in btn settings menu: {e}")
        await callback.answer("❌ Ошибка загрузки кнопок")

@router.callback_query(F.data == "admin_ui_btn_add")
async def admin_ui_btn_add(callback: types.CallbackQuery, state: FSMContext):
    """Начало добавления новой кнопки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    await state.set_state(AdminUIButtonStates.waiting_for_btn_text)
    await callback.message.answer(
        "✏️ Введите текст новой кнопки (макс. 30 символов):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_ui_btn_settings")]]
        )
    )

@router.callback_query(F.data.startswith("admin_ui_btn_edit_"))
async def admin_ui_btn_edit(callback: types.CallbackQuery, state: FSMContext):
    if not (callback.from_user and is_admin(callback.from_user.id)):
        if callback:
            await callback.answer("❌ Доступ запрещен")
        return
    if not (callback.data and callback.data.startswith("admin_ui_btn_edit_")):
        if callback:
            await callback.answer("Ошибка индекса")
        await admin_ui_btn_settings_menu(callback)
        return
    try:
        idx = int(callback.data.replace("admin_ui_btn_edit_", ""))
    except Exception:
        if callback:
            await callback.answer("Ошибка индекса")
        await admin_ui_btn_settings_menu(callback)
        return
    await state.update_data(edit_index=idx)
    await state.set_state(AdminUIButtonStates.waiting_for_btn_edit_index)
    import json
    btns = get_admin_setting('main_menu_btns', '[]')
    try:
        btns = json.loads(btns)
    except Exception:
        btns = []
    if 0 <= idx < len(btns):
        btn = btns[idx]
        if callback.message:
            await callback.message.answer(f"Текущий текст: {btn.get('text','')}. Введите новый текст:", reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_ui_btn_settings")]]
            ))
    else:
        if callback:
            await callback.answer("Ошибка индекса")
        await admin_ui_btn_settings_menu(callback)

# === УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЕЙ ===

@router.callback_query(F.data == "admin_delete_user")
async def admin_delete_user_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню удаления пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return

    text = "🗑️ <b>Удаление пользователя</b>\n\n"
    text += "Введите ID или @юзернейм пользователя для полного удаления:\n\n"
    text += "⚠️ <b>Внимание!</b> Это действие необратимо и удалит:\n"
    text += "• Профиль пользователя\n"
    text += "• Весь баланс и историю\n"
    text += "• Все заявки и заказы\n"
    text += "• Отзывы и активность\n"
    text += "• Рефералов и связи"

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_settings")]
    ])

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    await state.set_state(AdminSettingStates.waiting_for_user_to_delete)

@router.message(AdminSettingStates.waiting_for_user_to_delete)
async def process_user_deletion(message: types.Message, state: FSMContext):
    """Обработка ввода пользователя для удаления"""
    if not is_admin(message.from_user.id):
        return

    if not message.text:
        await message.answer("❌ Отправьте текстовое сообщение с ID или юзернеймом")
        return

    user_input = message.text.strip()
    if not user_input:
        await message.answer("❌ Введите корректный ID или юзернейм")
        return

    try:
        # Пробуем найти пользователя по ID или юзернейму
        user = None

        # Нормализуем поисковый запрос
        if user_input.startswith('@'):
            # Поиск по юзернейму - убираем @ и приводим к нижнему регистру
            username = user_input[1:].lower()
            user = get_user_by_username(username)
        elif user_input.isdigit():
            # Поиск по tg_id
            tg_id = int(user_input)
            user_profile = get_user_profile(tg_id)
            if user_profile:
                user = {
                    'tg_id': user_profile['tg_id'],
                    'username': user_profile['username'],
                    'full_name': user_profile['full_name'],
                    'balance': user_profile['balance']
                }
        else:
            # Пробуем как юзернейм без @ - приводим к нижнему регистру
            username = user_input.lower()
            user = get_user_by_username(username)

        if not user:
            await message.answer(f"❌ Пользователь '{user_input}' не найден")
            return

        user_tg_id = user['tg_id']
        user_username = user.get('username', '')
        user_full_name = user.get('full_name', 'Неизвестно')
        user_balance = user.get('balance', 0)

        username_display = f"@{user_username}" if user_username else f"ID: {user_tg_id}"

        # Показываем подтверждение удаления
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🗑️ Да, удалить", callback_data=f"confirm_delete_user_{user_tg_id}")],
            [types.InlineKeyboardButton(text="❌ Отмена", callback_data="admin_delete_user")]
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
        logging.error(f"Ошибка при поиске пользователя для удаления: {e}")
        await message.answer(f"❌ Ошибка при поиске пользователя: {str(e)}")
        await state.clear()

@router.callback_query(F.data.startswith("confirm_delete_user_"))
async def confirm_user_deletion(callback: types.CallbackQuery):
    """Подтверждение удаления пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return

    try:
        tg_id = int(callback.data.split("_")[-1])

        # Получаем информацию о пользователе перед удалением
        user_profile = get_user_profile(tg_id)
        if not user_profile:
            await callback.answer("❌ Пользователь не найден")
            return

        username = user_profile.get('username', '')
        full_name = user_profile.get('full_name', 'Неизвестно')
        username_display = f"@{username}" if username else f"ID: {tg_id}"

        # Удаляем пользователя полностью
        delete_user_everywhere_full(tg_id)

        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_settings")]
        ])

        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer(
            f"✅ <b>Пользователь удален</b>\n\n"
            f"<b>Удаленный пользователь:</b> {username_display}\n"
            f"<b>Имя:</b> {full_name}\n\n"
            f"🗑️ Все данные пользователя полностью удалены из системы:\n"
            f"• Профиль и баланс\n"
            f"• История операций\n"
            f"• Заявки и заказы\n"
            f"• Отзывы и активность\n"
            f"• Реферальные связи",
            parse_mode="HTML",
            reply_markup=kb
        )

    except Exception as e:
        logging.error(f"Ошибка при удалении пользователя: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)[:50]}...")

        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_settings")]
        ])

        try:
            await callback.message.edit_text(
                f"❌ <b>Ошибка при удалении пользователя</b>\n\n"
                f"Произошла ошибка: {str(e)}\n\n"
                f"Попробуйте еще раз или обратитесь к разработчику.",
                parse_mode="HTML",
                reply_markup=kb
            )
        except:
            await callback.message.answer(
                f"❌ <b>Ошибка при удалении пользователя</b>\n\n"
                f"Произошла ошибка: {str(e)}\n\n"
                f"Попробуйте еще раз или обратитесь к разработчику.",
                parse_mode="HTML",
                reply_markup=kb
            )

