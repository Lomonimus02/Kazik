from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def rewards_menu_kb():
    """Главное меню системы наград"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🎯 Доступные награды", callback_data="available_rewards")
    keyboard.button(text="🏆 Мои достижения", callback_data="my_achievements")
    keyboard.button(text="📊 Статистика", callback_data="rewards_stats")
    keyboard.button(text="⬅️ Назад", callback_data="main_menu")
    keyboard.adjust(1)
    return keyboard.as_markup()

def available_rewards_kb(achievements):
    """Клавиатура доступных наград"""
    keyboard = InlineKeyboardBuilder()
    
    if achievements:
        for achievement in achievements[:5]:  # Показываем первые 5
            achievement_id, name, description, type_, requirement, reward_type, reward_amount, is_active = achievement
            keyboard.button(
                text=f"🎯 {name} - {reward_amount}₽",
                callback_data=f"claim_reward_{achievement_id}"
            )
    
    # Навигация если наград больше 5
    if len(achievements) > 5:
        keyboard.button(text="➡️ Следующие", callback_data="rewards_page_1")
    
    keyboard.button(text="⬅️ Назад", callback_data="rewards")
    keyboard.adjust(1)
    return keyboard.as_markup()

def my_achievements_kb():
    """Клавиатура моих достижений"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="⬅️ Назад", callback_data="rewards")
    keyboard.adjust(1)
    return keyboard.as_markup()

def rewards_stats_kb():
    """Клавиатура статистики наград"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="⬅️ Назад", callback_data="rewards")
    keyboard.adjust(1)
    return keyboard.as_markup()

def rewards_pagination_kb(achievements, current_page, per_page):
    """Клавиатура пагинации наград"""
    keyboard = InlineKeyboardBuilder()
    
    total_pages = (len(achievements) + per_page - 1) // per_page
    
    # Кнопки навигации
    nav_row = []
    if current_page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"rewards_page_{current_page-1}"))
    
    nav_row.append(InlineKeyboardButton(text=f"{current_page+1}/{total_pages}", callback_data="no_action"))
    
    if current_page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"rewards_page_{current_page+1}"))
    
    if nav_row:
        keyboard.row(*nav_row)
    
    keyboard.button(text="⬅️ Назад", callback_data="available_rewards")
    keyboard.adjust(1)
    return keyboard.as_markup()

def rewards_admin_kb():
    """Админская клавиатура системы наград"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📊 Статистика", callback_data="admin_rewards_stats")
    keyboard.button(text="🏆 ТОП пользователей", callback_data="admin_rewards_top")
    keyboard.button(text="⚙️ Настройки", callback_data="admin_rewards_settings")
    keyboard.button(text="⬅️ Назад", callback_data="admin_panel")
    keyboard.adjust(1)
    return keyboard.as_markup()

def rewards_admin_stats_kb():
    """Клавиатура админской статистики"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="⬅️ Назад", callback_data="admin_rewards")
    keyboard.adjust(1)
    return keyboard.as_markup()

def rewards_admin_top_kb():
    """Клавиатура ТОП пользователей"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="⬅️ Назад", callback_data="admin_rewards")
    keyboard.adjust(1)
    return keyboard.as_markup()

def rewards_admin_settings_kb():
    """Клавиатура настроек системы наград"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🎯 Добавить достижение", callback_data="admin_rewards_add")
    keyboard.button(text="✏️ Редактировать", callback_data="admin_rewards_edit")
    keyboard.button(text="❌ Удалить", callback_data="admin_rewards_delete")
    keyboard.button(text="🔄 Сбросить статистику", callback_data="admin_rewards_reset")
    keyboard.button(text="⬅️ Назад", callback_data="admin_rewards")
    keyboard.adjust(1)
    return keyboard.as_markup() 