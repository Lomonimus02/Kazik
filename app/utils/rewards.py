import logging
from typing import Optional
from app.database.models import (
    get_user_engagement_stats, update_user_engagement_stats, 
    check_and_award_achievements, get_referrals_count, get_user_profile
)

logger = logging.getLogger(__name__)

async def update_user_stats_and_check_achievements(user_id: int, stat_type: str, value: int, bot=None):
    """Обновляет статистику пользователя и проверяет достижения"""
    try:
        # Обновляем статистику
        update_user_engagement_stats(user_id, stat_type, value)
        
        # Проверяем и выдаем достижения
        awarded = check_and_award_achievements(user_id, stat_type)
        
        # Уведомляем админов о полученных наградах
        if awarded and bot:
            from app.utils.misc import notify_admins
            for achievement in awarded:
                await notify_admins(
                    bot,
                    f"🏆 <b>Новый трофей у пользователя ID: {user_id}</b>\n"
                    f"➕ Получено: {achievement['reward_amount']}₽ за \"{achievement['description']}\"",
                    parse_mode="HTML"
                )
        
        return awarded
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении статистики пользователя {user_id}: {e}")
        return []

async def update_referral_stats(user_id: int, bot=None):
    """Обновляет статистику рефералов пользователя"""
    try:
        referrals_count = get_referrals_count(user_id)
        return await update_user_stats_and_check_achievements(user_id, 'invites', referrals_count, bot)
    except Exception as e:
        logger.error(f"Ошибка при обновлении статистики рефералов для {user_id}: {e}")
        return []

async def update_purchase_stats(user_id: int, bot=None):
    """Обновляет статистику покупок пользователя"""
    try:
        # Получаем профиль пользователя для подсчета покупок
        profile = get_user_profile(user_id)
        if profile:
            # Здесь нужно добавить логику подсчета выполненных покупок
            # Пока используем заглушку
            purchases_count = 0  # TODO: Реализовать подсчет покупок
            return await update_user_stats_and_check_achievements(user_id, 'purchases', purchases_count, bot)
        return []
    except Exception as e:
        logger.error(f"Ошибка при обновлении статистики покупок для {user_id}: {e}")
        return []

async def update_roulette_stats(user_id: int, bot=None):
    """Обновляет статистику игр в рулетку пользователя"""
    try:
        # Получаем текущую статистику
        stats = get_user_engagement_stats(user_id)
        current_games = stats[5] if len(stats) > 5 else 0
        
        # Увеличиваем количество игр
        new_games = current_games + 1
        
        return await update_user_stats_and_check_achievements(user_id, 'roulette', new_games, bot)
    except Exception as e:
        logger.error(f"Ошибка при обновлении статистики рулетки для {user_id}: {e}")
        return []

def get_achievement_progress(user_id: int, achievement_type: str) -> dict:
    """Получает прогресс пользователя к достижениям"""
    try:
        stats = get_user_engagement_stats(user_id)
        
        if achievement_type == 'invites':
            current = stats[2]  # total_invites
        elif achievement_type == 'purchases':
            current = stats[4]  # total_purchases
        elif achievement_type == 'roulette':
            current = stats[5] if len(stats) > 5 else 0  # total_roulette_games
        else:
            current = 0
        
        return {
            'current': current,
            'type': achievement_type
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении прогресса для {user_id}: {e}")
        return {'current': 0, 'type': achievement_type}

def format_achievement_progress(current: int, required: int, name: str) -> str:
    """Форматирует прогресс достижения для отображения"""
    progress = min(100, (current / required) * 100) if required > 0 else 0
    
    if progress >= 100:
        return f"✅ {name} - Готово к получению!"
    else:
        return f"⏳ {name} - {current}/{required} ({progress:.0f}%)"

async def check_all_user_achievements(user_id: int, bot=None) -> list:
    """Проверяет все достижения пользователя"""
    try:
        # Обновляем статистику рефералов
        await update_referral_stats(user_id, bot)
        
        # Обновляем статистику покупок
        await update_purchase_stats(user_id, bot)
        
        # Проверяем все достижения
        awarded = check_and_award_achievements(user_id)
        
        return awarded
        
    except Exception as e:
        logger.error(f"Ошибка при проверке достижений для {user_id}: {e}")
        return [] 