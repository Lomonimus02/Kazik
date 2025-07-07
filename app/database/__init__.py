"""
Модуль базы данных
"""
import logging

from .models import init_db

logger = logging.getLogger(__name__)

def initialize_database():
    """Инициализирует базу данных с логированием"""
    try:
        logger.info("Начало инициализации базы данных...")
        init_db()
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")
        raise

__all__ = ['init_db', 'initialize_database']
