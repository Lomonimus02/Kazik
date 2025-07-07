"""
Главный модуль Telegram-бота
"""
import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import BOT_TOKEN
from app.handlers import register_user_handlers
from app.database import init_db

# Настройка логирования
def setup_logging():
    """Настраивает систему логирования"""
    # Создаем директорию для логов если её нет
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Настройка форматирования
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Файловый обработчик
    file_handler = logging.FileHandler(
        log_dir / 'bot.log',
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Создаем логгер для бота
    logger = logging.getLogger(__name__)
    logger.info("Логирование настроено")
    
    return logger

async def main():
    """Главная функция запуска бота"""
    # Настраиваем логирование
    logger = setup_logging()
    
    try:
        # Инициализируем базу данных
        logger.info("Инициализация базы данных...")
        init_db()
        logger.info("База данных инициализирована")
        
        # Создаем бота и диспетчер
        logger.info("Создание бота и диспетчера...")
        bot = Bot(
            token=BOT_TOKEN, 
            default=DefaultBotProperties(parse_mode="HTML")
        )
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        # Регистрируем обработчики
        logger.info("Регистрация обработчиков...")
        register_user_handlers(dp)
        logger.info("Обработчики зарегистрированы")
        
        # Запускаем бота
        logger.info("🤖 Бот запущен и готов к работе!")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        raise
    finally:
        logger.info("Бот остановлен")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)
