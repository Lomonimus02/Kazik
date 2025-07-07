"""
Регистрация всех обработчиков бота
"""
import logging
from aiogram import Router

from . import user, support, admin_settings, slot_machine, activity_calendar, debug, admin

logger = logging.getLogger(__name__)

def register_user_handlers(dp: Router):
    """Регистрация всех пользовательских обработчиков"""
    try:
        logger.info("Регистрация обработчиков пользователя...")
        dp.include_router(user.router)

        logger.info("Регистрация админских настроек...")
        dp.include_router(admin_settings.router)

        logger.info("Регистрация обработчиков поддержки...")
        dp.include_router(support.router)

        logger.info("Регистрация обработчиков слот-машины...")
        dp.include_router(slot_machine.router)

        logger.info("Регистрация обработчиков календаря активности...")
        dp.include_router(activity_calendar.router)

        logger.info("Регистрация отладочных обработчиков...")
        dp.include_router(debug.router)

        logger.info("Регистрация админских обработчиков...")
        dp.include_router(admin.router)

        logger.info("Все обработчики успешно зарегистрированы")

    except Exception as e:
        logger.error(f"Ошибка при регистрации обработчиков: {e}")
        raise
