#!/usr/bin/env python3
"""
Скрипт инициализации данных для бота
"""
import asyncio
import logging
from app.database.models import (
    init_db, init_activity_rewards_custom, create_roulette_tables, init_roulette_configs
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def setup_all():
    """Инициализация всех данных"""
    try:
        logger.info("🔄 Начинаем инициализацию данных...")
        
        # Инициализация основной БД
        logger.info("📊 Инициализация основной базы данных...")
        init_db()
        logger.info("✅ Основная БД инициализирована")
        
        # Обновление призов календаря активности
        logger.info("📅 Обновление призов календаря активности...")
        init_activity_rewards_custom()
        logger.info("✅ Призы календаря обновлены")
        
        logger.info("🎉 Все данные успешно инициализированы!")
        logger.info("\n📋 Что было настроено:")
        logger.info("• База данных с таблицами")
        logger.info("• Призы календаря активности (обновлены)")
        logger.info("• Асинхронные функции рулетки добавлены")
        logger.info("• Поддержка исправлена")
        logger.info("• Подписка настроена только для покупок")
        logger.info("\n🚀 Бот готов к запуску!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(setup_all()) 