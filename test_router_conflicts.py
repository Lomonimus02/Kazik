#!/usr/bin/env python3
"""
Тест для проверки конфликтов роутеров
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext

@pytest.mark.asyncio
async def test_admin_settings_router_priority():
    """Тест приоритета роутера admin_settings"""
    print("🔍 Тестируем приоритет роутеров...")
    
    # Импортируем обработчики
    from app.handlers.admin_settings import (
        process_referral_username,
        AdminSettingStates
    )
    from app.handlers.support import handle_admin_reply
    
    # Создаем мок объекты
    message = AsyncMock()
    message.from_user = types.User(id=123456789, is_bot=False, first_name="Admin")
    message.text = "testuser"
    message.answer = AsyncMock()
    message.chat = AsyncMock()
    message.chat.type = 'private'
    
    state = AsyncMock()
    state.get_state.return_value = AdminSettingStates.waiting_for_referral_username
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    
    # Мокаем функции
    with patch('app.handlers.admin_settings.is_admin', return_value=True), \
         patch('app.handlers.admin_settings.get_user_by_username', return_value={
             'id': 123,
             'tg_id': 123456789,
             'username': 'testuser',
             'full_name': 'Test User',
             'referral_percent': 5.0
         }), \
         patch('app.handlers.support.is_admin', return_value=True):
        
        # Тест 1: Проверяем, что support handler не перехватывает сообщения в состоянии
        print("📋 Тест 1: Support handler с активным состоянием")
        
        # Вызываем support handler - он должен вернуться без обработки
        result = await handle_admin_reply(message, state)
        
        # Проверяем, что support handler не отправил ответ
        message.answer.assert_not_called()
        print("✅ Support handler корректно игнорирует сообщения в состоянии")
        
        # Тест 2: Проверяем, что admin_settings handler работает
        print("📋 Тест 2: Admin settings handler")
        
        # Сбрасываем моки
        message.answer.reset_mock()
        
        # Вызываем admin_settings handler
        await process_referral_username(message, state)
        
        # Проверяем, что admin_settings handler обработал сообщение
        state.update_data.assert_called_once()
        print("✅ Admin settings handler корректно обрабатывает сообщения")
        
        # Тест 3: Проверяем support handler без состояния и без активной сессии
        print("📋 Тест 3: Support handler без состояния и сессии")
        
        # Сбрасываем моки
        message.answer.reset_mock()
        state.get_state.return_value = None
        
        # Очищаем admin_sessions
        import app.handlers.support
        app.handlers.support.admin_sessions.clear()
        
        # Вызываем support handler - он должен вернуться без обработки
        result = await handle_admin_reply(message, state)
        
        # Проверяем, что support handler не отправил ответ
        message.answer.assert_not_called()
        print("✅ Support handler корректно игнорирует сообщения без активной сессии")

@pytest.mark.asyncio
async def test_photo_upload_workflow():
    """Тест полного workflow загрузки фото"""
    print("📸 Тестируем workflow загрузки фото...")
    
    from app.handlers.admin_settings import (
        admin_ui_photo_settings_menu,
        admin_setting_handler,
        process_setting_value,
        AdminSettingStates
    )
    
    # Тест 1: Переход в меню фото
    print("📋 Тест 1: Переход в меню фото")
    
    callback = AsyncMock()
    callback.from_user = types.User(id=123456789, is_bot=False, first_name="Admin")
    callback.message = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    
    state = AsyncMock()
    
    with patch('app.handlers.admin_settings.is_admin', return_value=True):
        await admin_ui_photo_settings_menu(callback)

        # Проверяем, что меню было показано
        callback.message.answer.assert_called_once()
        print("✅ Меню фото отображается корректно")
    
    # Тест 2: Выбор настройки фото
    print("📋 Тест 2: Выбор настройки фото")
    
    callback.data = "admin_setting_main_photo"
    callback.message.answer.reset_mock()
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    
    with patch('app.handlers.admin_settings.is_admin', return_value=True), \
         patch('app.handlers.admin_settings.get_admin_setting', return_value="current_photo_id"):
        
        await admin_setting_handler(callback, state)
        
        # Проверяем, что состояние было установлено
        state.set_state.assert_called_with(AdminSettingStates.waiting_for_value)
        assert state.update_data.call_count == 2  # Вызывается дважды для setting_key и prev_menu
        print("✅ Состояние для загрузки фото установлено корректно")
    
    # Тест 3: Загрузка фото
    print("📋 Тест 3: Загрузка фото")
    
    message = AsyncMock()
    message.from_user = types.User(id=123456789, is_bot=False, first_name="Admin")
    message.photo = [
        types.PhotoSize(file_id="large_photo", file_unique_id="large", width=800, height=600, file_size=50000)
    ]
    message.text = None
    message.answer = AsyncMock()
    
    state.get_data.return_value = {
        'setting_key': 'main_photo',
        'prev_menu': 'admin_ui_photo_settings'
    }
    state.clear = AsyncMock()
    
    with patch('app.handlers.admin_settings.is_admin', return_value=True), \
         patch('app.handlers.admin_settings.update_admin_setting') as mock_update, \
         patch('app.handlers.admin_settings.admin_ui_photo_settings_menu') as mock_menu:
        
        await process_setting_value(message, state)
        
        # Проверяем, что фото было сохранено
        mock_update.assert_called_once_with('main_photo', 'large_photo')
        
        # Проверяем, что состояние было очищено
        state.clear.assert_called_once()
        
        # Проверяем, что пользователь получил подтверждение
        message.answer.assert_called()
        
        print("✅ Загрузка фото работает корректно")

if __name__ == "__main__":
    asyncio.run(test_admin_settings_router_priority())
    asyncio.run(test_photo_upload_workflow())
    print("🎉 Все тесты пройдены!")
