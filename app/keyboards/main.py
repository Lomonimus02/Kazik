"""
Клавиатуры для бота
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.database.models import get_admin_setting, get_flag, calculate_stars_price

# Фиксированные цены на Premium (в рублях)
PREMIUM_FIXED_PRICES = {
    '3m': 1154,  # 3 месяца
    '6m': 1580,  # 6 месяцев
    '12m': 2600  # 12 месяцев
}

def main_menu_inline_kb():
    btn_premium = get_admin_setting('btn_premium', 'TG Премиум 🧿')
    btn_stars = get_admin_setting('btn_stars', 'Звезды ⭐')
    btn_crypto = get_admin_setting('btn_crypto', 'Купить криптовалюту 💸')
    btn_calendar = get_admin_setting('btn_calendar', 'Календарь активности 📅')
    btn_slot = get_admin_setting('btn_slot', 'Слот-машина 🎰')
    btn_support = get_admin_setting('btn_support', 'Поддержка ✍️')
    btn_reviews = get_admin_setting('btn_reviews', 'Отзывы 🛍️')
    btn_about = get_admin_setting('btn_about', 'Описание 📝')
    btn_profile = get_admin_setting('btn_profile', 'Профиль 👤')
    ref_flag =  get_flag('ref_active', 'true')
    keyboard = [
        [InlineKeyboardButton(text=btn_premium, callback_data="tg_premium"), InlineKeyboardButton(text=btn_stars, callback_data="stars")],
        [InlineKeyboardButton(text=btn_crypto, callback_data="crypto")],
        [InlineKeyboardButton(text=btn_calendar, callback_data="activity"), InlineKeyboardButton(text=btn_slot, callback_data="slot_machine")],
        [InlineKeyboardButton(text=btn_support, callback_data="support")],
        [InlineKeyboardButton(text=btn_reviews, callback_data="reviews"), InlineKeyboardButton(text=btn_about, callback_data="about")],
        [InlineKeyboardButton(text=btn_profile, callback_data="profile")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def stars_menu_inline_kb():
    prices = {50: 85, 75: 127, 100: 165, 150: 248, 200: 340, 250: 413, 350: 578, 500: 825, 700: 1155, 1000: 1640}
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"50⭐({prices[50]} RUB)", callback_data="stars_50"), InlineKeyboardButton(text=f"75⭐({prices[75]} RUB)", callback_data="stars_75")],
            [InlineKeyboardButton(text=f"100⭐({prices[100]} RUB)", callback_data="stars_100"), InlineKeyboardButton(text=f"150⭐({prices[150]} RUB)", callback_data="stars_150")],
            [InlineKeyboardButton(text=f"200⭐({prices[200]} RUB)", callback_data="stars_200"), InlineKeyboardButton(text=f"250⭐({prices[250]} RUB)", callback_data="stars_250")],
            [InlineKeyboardButton(text=f"350⭐({prices[350]} RUB)", callback_data="stars_350"), InlineKeyboardButton(text=f"500⭐({prices[500]} RUB)", callback_data="stars_500")],
            [InlineKeyboardButton(text=f"700⭐({prices[700]} RUB)", callback_data="stars_700"), InlineKeyboardButton(text=f"1000⭐({prices[1000]} RUB)", callback_data="stars_1000")],
            [InlineKeyboardButton(text="Другое количество⭐", callback_data="stars_custom"), InlineKeyboardButton(text="⬅️Назад", callback_data="main_menu")]
        ]
    )

def premium_menu_inline_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"3 месяца — {PREMIUM_FIXED_PRICES['3m']}₽", callback_data="premium_3m")],
            [InlineKeyboardButton(text=f"6 месяцев — {PREMIUM_FIXED_PRICES['6m']}₽", callback_data="premium_6m")],
            [InlineKeyboardButton(text=f"12 месяцев — {PREMIUM_FIXED_PRICES['12m']}₽", callback_data="premium_12m")],
            [InlineKeyboardButton(text="⬅️Назад", callback_data="main_menu")]
        ]
    )

def premium_pay_methods_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📱СБП", callback_data="pay_sbp_premium"), InlineKeyboardButton(text="💰Криптовалюта", callback_data="pay_crypto_premium")],
            [InlineKeyboardButton(text="⬅️Назад", callback_data="tg_premium")]
        ]
    )

def crypto_menu_inline_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💎 Toncoin (TON)", callback_data="crypto_ton")],
            [InlineKeyboardButton(text="🪙 Notcoin (NOT)", callback_data="crypto_not"), InlineKeyboardButton(text="🐶 DOGS (DOGS)", callback_data="crypto_dogs")],
            [InlineKeyboardButton(text="💬 Другая криптовалюта", callback_data="crypto_other")],
            [InlineKeyboardButton(text="⬅️Назад", callback_data="main_menu")]
        ]
    )

def pay_methods_kb(back_callback="main_menu"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📱СБП", callback_data="pay_sbp"), InlineKeyboardButton(text="💰Криптовалюта", callback_data="pay_crypto")],
            [InlineKeyboardButton(text="⬅️Назад", callback_data=back_callback)]
        ]
    )

def back_menu_kb(callback="main_menu"):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️Назад", callback_data=callback)]]
    )

def support_menu_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📞 Техническая поддержка", callback_data="support_contact")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
        ]
    )

def reviews_menu_inline_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Отзывы", url="https://t.me/legal_stars")],
            [InlineKeyboardButton(text="✍️ Оставить отзыв", callback_data="leave_review")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
        ]
    )

# Клавиатуры для системы вывода средств
def withdraw_confirm_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="withdraw_confirm")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="profile")],
        ]
    )

def withdraw_requisites_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Поддержка", url="https://t.me/legal_stars")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")],
        ]
    )

def admin_withdrawal_kb(withdrawal_id, user_id, amount, final_amount):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Выплатить", callback_data=f"withdraw_pay_{withdrawal_id}_{user_id}_{amount}_{final_amount}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"withdraw_reject_{withdrawal_id}_{user_id}_{amount}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"withdraw_delete_{withdrawal_id}")],
        ]
    )

def back_to_profile_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")],
        ]
    )

def slot_machine_kb():
    """Клавиатура для слот-машины"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎰 Крутить слоты", callback_data="spin_slot")],
            [InlineKeyboardButton(text="🎁 Получить бонус", callback_data="claim_referral_bonus")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="slot_stats")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
        ]
    )

def activity_calendar_kb():
    """Клавиатура для календаря активности"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Календарь", callback_data="activity_calendar")],
            [InlineKeyboardButton(text="🏆 Награды", callback_data="activity_rewards")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="activity_stats")],
            [InlineKeyboardButton(text="✅ Отметить активность", callback_data="mark_activity")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
        ]
    )

def admin_settings_kb():
    """
    Компактная клавиатура для админских настроек
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎨 UI", callback_data="admin_ui_settings"),
                InlineKeyboardButton(text="💰 Цены", callback_data="admin_price_settings"),
                InlineKeyboardButton(text="⭐ Звёзды", callback_data="admin_stars_settings")
            ],
            [
                InlineKeyboardButton(text="🎰 Слоты", callback_data="admin_slot_settings"),
                InlineKeyboardButton(text="📅 Активность", callback_data="admin_activity_settings"),
                InlineKeyboardButton(text="👥 Рефералы", callback_data="admin_referral_percents")
            ],
            [
                InlineKeyboardButton(text="🎫 Билетики", callback_data="admin_slot_tickets"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data="admin_delete_user"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")
            ],
            [
                InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
            ]
        ]
    )

def admin_ui_settings_kb():
    """Компактная клавиатура для настроек интерфейса"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🖼️ Фото", callback_data="admin_ui_photo_settings"),
                InlineKeyboardButton(text="🔘 Кнопки", callback_data="admin_ui_btn_settings"),
                InlineKeyboardButton(text="📝 Текст", callback_data="admin_ui_titles_settings")
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_settings")
            ]
        ]
    )

def admin_price_settings_kb():
    """Компактная клавиатура для настроек цен"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"3 мес: {PREMIUM_FIXED_PRICES['3m']}₽", callback_data="admin_setting_prem_3"),
                InlineKeyboardButton(text=f"6 мес: {PREMIUM_FIXED_PRICES['6m']}₽", callback_data="admin_setting_prem_6"),
                InlineKeyboardButton(text=f"12 мес: {PREMIUM_FIXED_PRICES['12m']}₽", callback_data="admin_setting_prem_12")
            ],
            [
                InlineKeyboardButton(text="💸 Комиссия", callback_data="admin_setting_withdrawal_commission")
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_settings")
            ]
        ]
    )

def admin_stars_settings_kb():
    """Компактная клавиатура для настроек звезд"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Курс <1500", callback_data="admin_setting_stars_rate_low"),
                InlineKeyboardButton(text="Курс >1500", callback_data="admin_setting_stars_rate_high")
            ],
            [
                InlineKeyboardButton(text="Порог", callback_data="admin_setting_stars_threshold")
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_settings")
            ]
        ]
    )

def admin_slot_settings_kb():
    """Компактная клавиатура для настроек слот-машины"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎯 Попытки", callback_data="admin_slot_attempts"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_setting_slot_daily_attempts")
            ],
            [
                InlineKeyboardButton(text="🕒 Сброс", callback_data="admin_setting_slot_reset_hour"),
                InlineKeyboardButton(text="📋 Комбинации", callback_data="slot_list_configs")
            ],
            [
                InlineKeyboardButton(text="➕ Добавить", callback_data="slot_add_config")
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_settings")
            ]
        ]
    )

def admin_panel_kb():
    """Компактная клавиатура админ-панели"""
    from app.config_flags import proverka, ref_active
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"🔍 {'✅' if proverka else '❌'}", callback_data="toggle_check"),
                InlineKeyboardButton(text=f"👥 {'✅' if ref_active else '❌'}", callback_data="toggle_ref"),
                InlineKeyboardButton(text="⚙️", callback_data="admin_settings")
            ],
            [
                InlineKeyboardButton(text="🎰", callback_data="admin_slot_wins"),
                InlineKeyboardButton(text="📅", callback_data="admin_activity_stats"),
                InlineKeyboardButton(text="📢", callback_data="rassilka")
            ],
            [
                InlineKeyboardButton(text="📂", callback_data="admin_db"),
                InlineKeyboardButton(text="🚫", callback_data="blacklist_menu"),
                InlineKeyboardButton(text="🗑", callback_data="delete_user")
            ],
            [
                InlineKeyboardButton(text="📋 Заявки", callback_data="admin_orders"),
                InlineKeyboardButton(text="💳 Выводы", callback_data="admin_withdrawals")
            ],
            [
                InlineKeyboardButton(text="💬 Тикеты", callback_data="admin_support_tickets"),
                InlineKeyboardButton(text="⭐ Отзывы", callback_data="admin_reviews")
            ],
            [
                InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
            ]
        ]
    )

def slot_win_admin_kb(win_id, user_id, reward_type, reward_amount):
    """Клавиатура для админских действий с выигрышем слот-машины"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"slot_win_confirm_{win_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"slot_win_reject_{win_id}")
            ],
            [
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"slot_win_delete_{win_id}")
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_slot_wins")
            ]
        ]
    )

def admin_activity_settings_kb():
    """Клавиатура для настроек активности"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Награды", callback_data="admin_activity_rewards"),
                InlineKeyboardButton(text="🔄 Вкл/Выкл", callback_data="admin_setting_activity_enabled")
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_settings")
            ]
        ]
    )
    
def admin_withdrawals_kb():
    """Клавиатура для просмотра заявок на вывод средств"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Очистить все заявки", callback_data="admin_clear_withdrawals")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")],
        ]
    )

def admin_orders_kb():
    """Клавиатура для просмотра заказов"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Очистить все заказы", callback_data="admin_clear_orders")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")],
        ]
    )

def admin_clear_withdrawals_kb():
    """Клавиатура для подтверждения очистки заявок на вывод"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить очистку", callback_data="admin_clear_withdrawals_confirm")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_withdrawals")],
        ]
    )

def admin_clear_orders_kb():
    """Клавиатура для подтверждения очистки заказов"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить очистку", callback_data="admin_clear_orders_confirm")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_orders")],
        ]
    )

def about_menu_inline_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
        ]
    )

def admin_support_tickets_kb(tickets):
    # tickets: List[Tuple] (id, user_id, username, full_name, message, status, ...)
    buttons = []
    for t in tickets:
        # Показываем username если есть, иначе full_name
        user_display = f"@{t[2]}" if t[2] else t[3][:16]
        btn_text = f"#{t[0]} | {user_display[:16]} | {t[5]}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"admin_support_ticket_{t[0]}")])

    # Добавляем кнопку удаления всех тикетов если есть тикеты
    if tickets:
        buttons.append([InlineKeyboardButton(text="🗑 Удалить все тикеты", callback_data="admin_clear_all_tickets")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_support_ticket_actions_kb(ticket_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить тикет", callback_data=f"admin_support_ticket_delete_{ticket_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_support_tickets")],
        ]
    )

def admin_clear_all_tickets_kb():
    """Клавиатура для подтверждения удаления всех тикетов"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить удаление", callback_data="admin_clear_all_tickets_confirm")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_support_tickets")],
        ]
    )