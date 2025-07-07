#!/usr/bin/env python3
"""
Финальный интеграционный тест для проверки исправлений админ панели
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext

@pytest.mark.asyncio
async def test_complete_admin_workflow():
    """Полный тест workflow админ панели"""
    print("🚀 Запуск полного интеграционного теста...")
    
    # Импортируем все необходимые функции
    from app.handlers.admin_settings import (
        admin_ui_photo_settings_menu,
        admin_setting_handler,
        process_setting_value,
        admin_referral_percents_menu,
        process_referral_username,
        process_referral_percent,
        admin_slot_tickets_menu,
        process_ticket_username,
        process_ticket_amount,
        AdminSettingStates
    )
    
    # === ТЕСТ 1: ЗАГРУЗКА ФОТО ===
    print("\n📸 Тест 1: Полный workflow загрузки фото")
    
    # Шаг 1: Переход в меню фото
    callback = AsyncMock()
    callback.from_user = types.User(id=123456789, is_bot=False, first_name="Admin")
    callback.message = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    
    with patch('app.handlers.admin_settings.is_admin', return_value=True):
        await admin_ui_photo_settings_menu(callback)
        callback.message.answer.assert_called_once()
        print("  ✅ Шаг 1: Меню фото открыто")
    
    # Шаг 2: Выбор настройки фото
    callback.data = "admin_setting_main_photo"
    callback.message.edit_text = AsyncMock()
    state = AsyncMock()
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    
    with patch('app.handlers.admin_settings.is_admin', return_value=True), \
         patch('app.handlers.admin_settings.get_admin_setting', return_value="current_photo"):
        
        await admin_setting_handler(callback, state)
        state.set_state.assert_called_with(AdminSettingStates.waiting_for_value)
        print("  ✅ Шаг 2: Состояние для загрузки установлено")
    
    # Шаг 3: Загрузка фото
    message = AsyncMock()
    message.from_user = types.User(id=123456789, is_bot=False, first_name="Admin")
    message.photo = [
        types.PhotoSize(file_id="new_photo_id", file_unique_id="new", width=800, height=600, file_size=50000)
    ]
    message.text = None
    message.answer = AsyncMock()
    
    state.get_data.return_value = {
        'setting_key': 'main_photo',
        'prev_menu': 'admin_ui_photo_settings'
    }
    state.clear = AsyncMock()
    
    with patch('app.handlers.admin_settings.is_admin', return_value=True), \
         patch('app.handlers.admin_settings.update_admin_setting') as mock_update:
        
        await process_setting_value(message, state)
        mock_update.assert_called_once_with('main_photo', 'new_photo_id')
        state.clear.assert_called_once()
        print("  ✅ Шаг 3: Фото успешно загружено и сохранено")
    
    # === ТЕСТ 2: УПРАВЛЕНИЕ РЕФЕРАЛАМИ ===
    print("\n👥 Тест 2: Полный workflow управления рефералами")
    
    # Шаг 1: Переход в меню рефералов
    callback = AsyncMock()
    callback.from_user = types.User(id=123456789, is_bot=False, first_name="Admin")
    callback.message = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    
    state = AsyncMock()
    state.set_state = AsyncMock()
    
    with patch('app.handlers.admin_settings.is_admin', return_value=True):
        await admin_referral_percents_menu(callback, state)
        state.set_state.assert_called_with(AdminSettingStates.waiting_for_referral_username)
        print("  ✅ Шаг 1: Меню рефералов открыто, состояние установлено")
    
    # Шаг 2: Ввод username
    message = AsyncMock()
    message.from_user = types.User(id=123456789, is_bot=False, first_name="Admin")
    message.text = "testuser"
    message.answer = AsyncMock()
    
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    
    with patch('app.handlers.admin_settings.is_admin', return_value=True), \
         patch('app.handlers.admin_settings.get_user_by_username', return_value={
             'id': 123,
             'tg_id': 987654321,
             'username': 'testuser',
             'full_name': 'Test User',
             'referral_percent': 5.0
         }):
        
        await process_referral_username(message, state)
        state.update_data.assert_called_once()
        state.set_state.assert_called_with(AdminSettingStates.waiting_for_referral_percent)
        print("  ✅ Шаг 2: Username найден, переход к вводу процента")
    
    # Шаг 3: Ввод процента
    message.text = "10.5"
    state.get_data.return_value = {
        'user_username': 'testuser'
    }
    state.update_data = AsyncMock()

    with patch('app.handlers.admin_settings.is_admin', return_value=True), \
         patch('app.handlers.admin_settings.update_user_referral_percent_by_username', return_value=True) as mock_update_ref:

        await process_referral_percent(message, state)
        mock_update_ref.assert_called_once_with('testuser', 10.5)
        state.update_data.assert_called_once_with(current_percent=10.5)
        print("  ✅ Шаг 3: Процент реферала успешно обновлен")
    
    # === ТЕСТ 3: ВЫДАЧА БИЛЕТИКОВ ===
    print("\n🎫 Тест 3: Полный workflow выдачи билетиков")
    
    # Шаг 1: Переход в меню билетиков
    callback = AsyncMock()
    callback.from_user = types.User(id=123456789, is_bot=False, first_name="Admin")
    callback.message = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    
    state = AsyncMock()
    state.set_state = AsyncMock()
    
    with patch('app.handlers.admin_settings.is_admin', return_value=True):
        await admin_slot_tickets_menu(callback, state)
        state.set_state.assert_called_with(AdminSettingStates.waiting_for_ticket_username)
        print("  ✅ Шаг 1: Меню билетиков открыто, состояние установлено")
    
    # Шаг 2: Ввод username для билетиков
    message = AsyncMock()
    message.from_user = types.User(id=123456789, is_bot=False, first_name="Admin")
    message.text = "ticketuser"
    message.answer = AsyncMock()
    
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    
    with patch('app.handlers.admin_settings.is_admin', return_value=True), \
         patch('app.handlers.admin_settings.get_user_by_username', return_value={
             'id': 456,
             'tg_id': 111222333,
             'username': 'ticketuser',
             'full_name': 'Ticket User'
         }):
        
        await process_ticket_username(message, state)
        state.update_data.assert_called_once()
        state.set_state.assert_called_with(AdminSettingStates.waiting_for_ticket_amount)
        print("  ✅ Шаг 2: Username для билетиков найден, переход к вводу количества")
    
    # Шаг 3: Ввод количества билетиков
    message.text = "5"
    message.bot = AsyncMock()
    message.bot.send_message = AsyncMock()

    state.get_data.return_value = {
        'ticket_user_id': 111222333,
        'ticket_username': 'ticketuser',
        'ticket_full_name': 'Ticket User'
    }
    state.clear = AsyncMock()

    with patch('app.handlers.admin_settings.is_admin', return_value=True), \
         patch('app.handlers.admin_settings.add_slot_attempts') as mock_add_attempts:

        mock_add_attempts.return_value = None  # async function
        await process_ticket_amount(message, state)
        mock_add_attempts.assert_called_once_with(111222333, 5)
        message.answer.assert_called()
        print("  ✅ Шаг 3: Билетики успешно выданы")
    
    print("\n🎉 Все интеграционные тесты пройдены успешно!")
    print("✅ Загрузка фото работает")
    print("✅ Управление рефералами работает") 
    print("✅ Выдача билетиков работает")

if __name__ == "__main__":
    asyncio.run(test_complete_admin_workflow())
