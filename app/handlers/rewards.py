import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.models import (
    get_engagement_achievements, get_user_achievements, get_user_engagement_stats,
    get_available_achievements, award_achievement, check_and_award_achievements,
    get_engagement_stats_summary, update_user_engagement_stats
)
from app.keyboards.rewards import (
    rewards_menu_kb, available_rewards_kb, my_achievements_kb,
    rewards_stats_kb, rewards_pagination_kb
)
from app.utils.misc import is_admin, notify_admins
from app.config import ADMINS

router = Router()
logger = logging.getLogger(__name__)

class RewardsStates(StatesGroup):
    """Состояния для системы наград"""
    waiting_for_claim_confirmation = State()

@router.callback_query(F.data == "rewards")
async def rewards_menu(callback: CallbackQuery):
    """Главное меню системы наград"""
    try:
        if not callback.message:
            return
        
        text = "🏆 <b>Система достижений и наград</b>\n\n"
        text += "Зарабатывайте награды за активность:\n"
        text += "• Приглашение друзей\n"
        text += "• Совершение покупок\n"
        text += "• Игры в рулетку\n\n"
        text += "Выберите раздел:"
        
        await callback.message.edit_text(
            text,
            reply_markup=rewards_menu_kb(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка в rewards_menu: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@router.callback_query(F.data == "available_rewards")
async def show_available_rewards(callback: CallbackQuery):
    """Показать доступные награды"""
    try:
        user_id = callback.from_user.id
        
        # Проверяем и выдаем достижения автоматически
        awarded = check_and_award_achievements(user_id)
        
        # Получаем доступные награды
        available = get_available_achievements(user_id)
        
        if not callback.message:
            return
        
        if not available:
            text = "🎯 <b>Доступные награды</b>\n\n"
            text += "У вас пока нет доступных достижений.\n"
            text += "Продолжайте быть активными!"
            
            if awarded:
                text += f"\n\n🎉 <b>Только что получено:</b>\n"
                for achievement in awarded:
                    text += f"• {achievement['name']} - {achievement['reward_amount']}₽\n"
        else:
            text = "🎯 <b>Доступные награды</b>\n\n"
            
            if awarded:
                text += "🎉 <b>Только что получено:</b>\n"
                for achievement in awarded:
                    text += f"• {achievement['name']} - {achievement['reward_amount']}₽\n"
                text += "\n"
            
            text += "Доступные для получения:\n"
            for i, achievement in enumerate(available[:5], 1):  # Показываем первые 5
                achievement_id, name, description, type_, requirement, reward_type, reward_amount, is_active = achievement
                text += f"{i}. <b>{name}</b>\n"
                text += f"   📝 {description}\n"
                text += f"   💰 Награда: {reward_amount}₽\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=available_rewards_kb(available),
            parse_mode="HTML"
        )
        
        # Уведомляем админов о полученных наградах
        if awarded:
            for achievement in awarded:
                await notify_admins(
                    callback.bot,
                    f"🏆 <b>Новый трофей у пользователя @{callback.from_user.username or 'Unknown'} (ID: {user_id})</b>\n"
                    f"➕ Получено: {achievement['reward_amount']}₽ за \"{achievement['description']}\"",
                    parse_mode="HTML"
                )
                
    except Exception as e:
        logger.error(f"Ошибка в show_available_rewards: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@router.callback_query(F.data == "my_achievements")
async def show_my_achievements(callback: CallbackQuery):
    """Показать мои достижения"""
    try:
        user_id = callback.from_user.id
        achievements = get_user_achievements(user_id)
        
        if not callback.message:
            return
        
        if not achievements:
            text = "🏆 <b>Мои достижения</b>\n\n"
            text += "У вас пока нет полученных достижений.\n"
            text += "Продолжайте быть активными, чтобы получить награды!"
        else:
            text = "🏆 <b>Мои достижения</b>\n\n"
            for achievement in achievements:
                achievement_id, user_id, achievement_id_db, achieved_at, reward_claimed, name, description, reward_type, reward_amount = achievement
                text += f"<b>{name}</b>\n"
                text += f"📝 {description}\n"
                text += f"💰 Награда: {reward_amount}₽\n"
                text += f"📅 Получено: {achieved_at[:10]}\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=my_achievements_kb(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка в show_my_achievements: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@router.callback_query(F.data == "rewards_stats")
async def show_rewards_stats(callback: CallbackQuery):
    """Показать статистику наград"""
    try:
        user_id = callback.from_user.id
        stats = get_user_engagement_stats(user_id)
        
        if not callback.message:
            return
        
        text = "📊 <b>Моя статистика</b>\n\n"
        text += f"👥 <b>Приглашено друзей:</b> {stats[2]}\n"
        text += f"🛒 <b>Покупок:</b> {stats[4]}\n"
        text += f"🎰 <b>Игр в рулетку:</b> {stats[5] if len(stats) > 5 else 0}\n"
        text += f"💰 <b>Сумма покупок:</b> {stats[5]:.0f}₽\n\n"
        
        # Показываем прогресс к следующим достижениям
        available = get_available_achievements(user_id)
        if available:
            text += "🎯 <b>Доступные достижения:</b>\n"
            for achievement in available[:3]:  # Показываем первые 3
                achievement_id, name, description, type_, requirement, reward_type, reward_amount, is_active = achievement
                current_value = 0
                if type_ == 'invites':
                    current_value = stats[2]
                elif type_ == 'purchases':
                    current_value = stats[4]
                elif type_ == 'roulette':
                    current_value = stats[5] if len(stats) > 5 else 0
                
                progress = min(100, (current_value / requirement) * 100)
                text += f"• {name}: {current_value}/{requirement} ({progress:.0f}%)\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=rewards_stats_kb(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка в show_rewards_stats: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@router.callback_query(F.data.startswith("claim_reward_"))
async def claim_reward(callback: CallbackQuery):
    """Получить награду"""
    try:
        if not callback.data:
            return
        
        achievement_id = int(callback.data.split("_")[2])
        user_id = callback.from_user.id
        
        success, message = award_achievement(user_id, achievement_id)
        
        if success:
            # Уведомляем админов
            await notify_admins(
                callback.bot,
                f"🏆 <b>Новый трофей у пользователя @{callback.from_user.username or 'Unknown'} (ID: {user_id})</b>\n"
                f"➕ Получено: {message}",
                parse_mode="HTML"
            )
            
            if callback.message:
                await callback.message.edit_text(
                    f"🎉 <b>Поздравляем!</b>\n\n{message}\n\n"
                    "Продолжайте быть активными для получения новых наград!",
                    reply_markup=rewards_menu_kb(),
                    parse_mode="HTML"
                )
        else:
            await callback.answer(message, show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка в claim_reward: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@router.callback_query(F.data.startswith("rewards_page_"))
async def rewards_pagination(callback: CallbackQuery):
    """Пагинация в списке наград"""
    try:
        page = int(callback.data.split("_")[2])
        user_id = callback.from_user.id
        available = get_available_achievements(user_id)
        
        if not callback.message:
            return
        
        per_page = 5
        start_idx = page * per_page
        end_idx = start_idx + per_page
        page_achievements = available[start_idx:end_idx]
        
        if not page_achievements and page > 0:
            page = 0
            start_idx = 0
            end_idx = per_page
            page_achievements = available[start_idx:end_idx]
        
        text = "🎯 <b>Доступные награды</b>\n\n"
        
        if not page_achievements:
            text += "У вас пока нет доступных достижений.\n"
            text += "Продолжайте быть активными!"
        else:
            for i, achievement in enumerate(page_achievements, start_idx + 1):
                achievement_id, name, description, type_, requirement, reward_type, reward_amount, is_active = achievement
                text += f"{i}. <b>{name}</b>\n"
                text += f"   📝 {description}\n"
                text += f"   💰 Награда: {reward_amount}₽\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=rewards_pagination_kb(available, page, per_page),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в rewards_pagination: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

# Админские команды
@router.message(Command("rewards_admin"))
async def rewards_admin_menu(message: Message):
    """Админское меню системы наград"""
    if not is_admin(message.from_user.id):
        await message.answer("Доступ запрещён")
        return
    
    try:
        stats = get_engagement_stats_summary()
        
        text = "🎯 <b>Админ-панель системы наград</b>\n\n"
        text += f"📊 <b>Общая статистика:</b>\n"
        text += f"• Выдано наград: {stats['total_awards']}\n"
        text += f"• Общая сумма бонусов: {stats['total_bonuses']:.0f}₽\n\n"
        
        text += "🔧 <b>Доступные действия:</b>\n"
        text += "• /rewards_stats - Подробная статистика\n"
        text += "• /rewards_top - ТОП пользователей\n"
        text += "• /rewards_reset - Сброс статистики\n"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка в rewards_admin_menu: {e}")
        await message.answer("Произошла ошибка")

@router.message(Command("rewards_stats"))
async def admin_rewards_stats(message: Message):
    """Подробная статистика системы наград"""
    if not is_admin(message.from_user.id):
        await message.answer("Доступ запрещён")
        return
    
    try:
        stats = get_engagement_stats_summary()
        
        text = "📊 <b>Подробная статистика системы наград</b>\n\n"
        text += f"🎯 <b>Общие показатели:</b>\n"
        text += f"• Всего выдано наград: {stats['total_awards']}\n"
        text += f"• Общая сумма бонусов: {stats['total_bonuses']:.0f}₽\n"
        text += f"• Средняя награда: {stats['total_bonuses'] / max(stats['total_awards'], 1):.0f}₽\n\n"
        
        text += "🏆 <b>ТОП-10 пользователей:</b>\n"
        for i, (user_id, count) in enumerate(stats['top_users'][:10], 1):
            text += f"{i}. ID {user_id}: {count} наград\n"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка в admin_rewards_stats: {e}")
        await message.answer("Произошла ошибка")

@router.message(Command("rewards_reset"))
async def admin_rewards_reset(message: Message):
    """Сброс статистики системы наград"""
    if not is_admin(message.from_user.id):
        await message.answer("Доступ запрещён")
        return
    
    try:
        # Здесь можно добавить логику сброса статистики
        await message.answer("⚠️ Функция сброса статистики в разработке")
        
    except Exception as e:
        logger.error(f"Ошибка в admin_rewards_reset: {e}")
        await message.answer("Произошла ошибка") 