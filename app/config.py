"""
Конфигурация бота
"""
import os
from typing import List

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "7861772909:AAHFjr8e5qfU94sAY5E3b4RzeFwWravWnGU")
ADMINS: List[int] = [int(admin_id) for admin_id in os.getenv("ADMINS", "7119152261, 829887947, 1115066615").split(',') if admin_id]

# ID чата поддержки
SUPPORT_CHAT_ID = os.getenv("SUPPORT_CHAT_ID", "-1002600416166")

def validate_config():
    """Проверяет корректность конфигурации"""
    if not BOT_TOKEN:
        raise ValueError("Не установлен токен бота. Установите переменную окружения BOT_TOKEN")
    
    if not ADMINS:
        raise ValueError("Не указаны администраторы бота")
    
    return True

# Валидация при импорте
if __name__ != "__main__":
    validate_config()