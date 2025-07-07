#!/usr/bin/env python3
"""
Диагностический скрипт для проверки состояний админ панели
"""
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_admin_states():
    """Тестирует состояния админ панели"""
    print("🔍 Диагностика состояний админ панели...")
    
    # Импортируем обработчики
    try:
        from app.handlers.admin_settings import (
            admin_referral_percents_menu, 
            admin_slot_tickets_menu,
            process_referral_username,
            process_ticket_username,
            AdminSettingStates
        )
        print("✅ Импорт обработчиков успешен")
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return
    
    # Создаем мок объекты
    storage = MemoryStorage()
    
    # Тест 1: Проверка установки состояния для рефералов
    print("\n📋 Тест 1: Состояние рефералов")
    try:
        callback = AsyncMock()
        callback.from_user = types.User(id=123456789, is_bot=False, first_name="Admin")
        callback.message = AsyncMock()
        callback.message.answer = AsyncMock()
        
        state = AsyncMock()
        state.set_state = AsyncMock()
        
        # Мокаем is_admin
        import app.handlers.admin_settings
        original_is_admin = app.handlers.admin_settings.is_admin
        app.handlers.admin_settings.is_admin = lambda x: True
        
        await admin_referral_percents_menu(callback, state)
        
        # Проверяем, что состояние было установлено
        state.set_state.assert_called_once_with(AdminSettingStates.waiting_for_referral_username)
        print("✅ Состояние для рефералов устанавливается правильно")
        
        # Восстанавливаем оригинальную функцию
        app.handlers.admin_settings.is_admin = original_is_admin
        
    except Exception as e:
        print(f"❌ Ошибка в тесте рефералов: {e}")
    
    # Тест 2: Проверка установки состояния для билетиков
    print("\n🎫 Тест 2: Состояние билетиков")
    try:
        callback = AsyncMock()
        callback.from_user = types.User(id=123456789, is_bot=False, first_name="Admin")
        callback.message = AsyncMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        
        state = AsyncMock()
        state.set_state = AsyncMock()
        
        # Мокаем is_admin
        import app.handlers.admin_settings
        original_is_admin = app.handlers.admin_settings.is_admin
        app.handlers.admin_settings.is_admin = lambda x: True
        
        await admin_slot_tickets_menu(callback, state)
        
        # Проверяем, что состояние было установлено
        state.set_state.assert_called_once_with(AdminSettingStates.waiting_for_ticket_username)
        print("✅ Состояние для билетиков устанавливается правильно")
        
        # Восстанавливаем оригинальную функцию
        app.handlers.admin_settings.is_admin = original_is_admin
        
    except Exception as e:
        print(f"❌ Ошибка в тесте билетиков: {e}")
    
    # Тест 3: Проверка обработки сообщений
    print("\n💬 Тест 3: Обработка сообщений")
    try:
        message = AsyncMock()
        message.from_user = types.User(id=123456789, is_bot=False, first_name="Admin")
        message.text = "testuser"
        message.answer = AsyncMock()
        
        state = AsyncMock()
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()
        
        # Мокаем функции базы данных
        import app.handlers.admin_settings
        original_is_admin = app.handlers.admin_settings.is_admin
        original_get_user = app.handlers.admin_settings.get_user_by_username
        
        app.handlers.admin_settings.is_admin = lambda x: True
        app.handlers.admin_settings.get_user_by_username = lambda x: {
            'id': 123,
            'tg_id': 123456789,
            'username': 'testuser',
            'full_name': 'Test User',
            'referral_percent': 5.0
        }
        
        await process_referral_username(message, state)
        
        # Проверяем, что данные были сохранены
        state.update_data.assert_called_once()
        print("✅ Обработка сообщений работает правильно")
        
        # Восстанавливаем оригинальные функции
        app.handlers.admin_settings.is_admin = original_is_admin
        app.handlers.admin_settings.get_user_by_username = original_get_user
        
    except Exception as e:
        print(f"❌ Ошибка в тесте обработки сообщений: {e}")
    
    print("\n🎉 Диагностика завершена!")

if __name__ == "__main__":
    asyncio.run(test_admin_states())
