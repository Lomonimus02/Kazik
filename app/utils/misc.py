"""
Утилиты для бота
"""
import logging
import asyncio
from typing import Optional, List, Dict, Any
from aiogram import Bot

from app.config import ADMINS
from app.database.models import add_referral_bonus_for_order_async, get_flag

logger = logging.getLogger(__name__)

async def notify_admins(bot: Bot, text: str, reply_markup=None, parse_mode=None, document=None, document_caption=None):
    """Отправляет уведомление всем админам"""
    if not ADMINS:
        logger.warning("Список администраторов пуст")
        return
    
    success_count = 0
    for admin_id in ADMINS:
        try:
            if document:
                await bot.send_document(admin_id, document, caption=document_caption, reply_markup=reply_markup, parse_mode=parse_mode)
            else:
                await bot.send_message(admin_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
            success_count += 1
            logger.debug(f"Уведомление отправлено админу {admin_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу {admin_id}: {e}")
            continue
    
    logger.info(f"Уведомления отправлены {success_count}/{len(ADMINS)} админам")

async def notify_admin(bot, admin_id: int, text: str, reply_markup=None, parse_mode="HTML"):
    """Отправляет уведомление конкретному админу"""
    try:
        await bot.send_message(
            admin_id,
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        logger.debug(f"Уведомление отправлено админу {admin_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления админу {admin_id}: {e}")
        return False

async def check_user_premium_status(bot, user_id: int) -> bool:
    """
    Проверяет, является ли пользователь Telegram Premium
    В реальном боте здесь должна быть проверка через Telegram API
    """
    try:
        # В будущем здесь можно добавить реальную проверку через Telegram API
        # Пока возвращаем True для тестирования
        return True
    except Exception as e:
        logger.error(f"Error checking premium status: {e}")
        return False

def format_number(number: float) -> str:
    """Форматирует число для красивого отображения"""
    if number >= 1000000:
        return f"{number/1000000:.1f}M"
    elif number >= 1000:
        return f"{number/1000:.1f}K"
    else:
        return f"{number:.0f}"

def safe_int(value, default: int = 0) -> int:
    """Безопасно преобразует значение в целое число"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value, default: float = 0.0) -> float:
    """Безопасно преобразует значение в число с плавающей точкой"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

async def retry_async(func, max_retries: int = 3, delay: float = 1.0):
    """Выполняет асинхронную функцию с повторными попытками"""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Функция {func.__name__} не выполнена после {max_retries} попыток: {e}")
                raise
            logger.warning(f"Попытка {attempt + 1} функции {func.__name__} не удалась: {e}")
            await asyncio.sleep(delay * (attempt + 1))

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом"""
    return user_id in ADMINS

async def process_referral_bonus(bot: Bot, user_id: int, order_amount: float, order_type: str, order_id: int) -> bool:
    """
    Централизованная функция для обработки реферальных бонусов
    Возвращает True если бонус был успешно начислен
    """
    if not get_flag('ref_active', 'true'):
        return False
        
    try:
        success, bonus_data = await add_referral_bonus_for_order_async(user_id, order_amount, order_type)
        if success and bonus_data:
            # Уведомляем админов о реферальном бонусе
            await notify_admins(
                bot,
                f"💸 Реферальный бонус: <b>{bonus_data['bonus_amount']:.2f}₽</b> начислен пригласившему "
                f"<b>{bonus_data['referrer_name']}</b> (@{bonus_data['referrer_username']}) "
                f"за покупку {order_type} его рефералом.",
                parse_mode="HTML"
            )
            
            # Уведомляем пригласившего
            await bot.send_message(
                bonus_data['referrer_tg_id'],
                f"🎉 Ваш реферал совершил покупку {order_type}!\n"
                f"Вам начислено <b>{bonus_data['bonus_amount']:.2f}₽</b> "
                f"({bonus_data['referral_percent']}% от суммы покупки)",
                parse_mode="HTML"
            )
            
            logger.info(f"[REFERRAL] Начислен бонус {bonus_data['bonus_amount']:.2f}₽ пользователю {bonus_data['referrer_tg_id']} за заказ {order_id}")
            return True
        else:
            logger.info(f"[REFERRAL] Реферальный бонус не начислен для заказа {order_id}")
            return False
            
    except Exception as e:
        logger.error(f"[REFERRAL] Ошибка обработки реферального бонуса для заказа {order_id}: {e}")
        return False
