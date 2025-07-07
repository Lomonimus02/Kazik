#!/usr/bin/env python3
"""
Скрипт для запуска Telegram бота Legal Stars
"""
import asyncio
import os
import sys
import logging
from pathlib import Path

# Добавляем текущую директорию в Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Импортируем и запускаем бота
from app.main import main

def check_environment():
    """Проверяет окружение перед запуском"""
    # Проверяем наличие необходимых файлов
    required_files = [
        "app/config.py",
        "app/main.py",
        "app/database/models.py"
    ]
    
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"❌ Отсутствует необходимый файл: {file_path}")
            return False
    
    # Проверяем наличие токена
    try:
        from app.config import BOT_TOKEN
        if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN":
            print("❌ Не установлен токен бота в config.py")
            return False
    except ImportError:
        print("❌ Не удалось импортировать конфигурацию")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Запуск Telegram бота Legal Stars...")
    print("=" * 50)
    
    # Проверяем окружение
    if not check_environment():
        print("❌ Проверка окружения не пройдена")
        sys.exit(1)
    
    print("✅ Окружение проверено")
    print("📝 Для остановки нажмите Ctrl+C")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Критическая ошибка запуска бота: {e}")
        logging.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1) 