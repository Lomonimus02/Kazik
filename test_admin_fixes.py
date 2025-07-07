"""
Тесты для проверки исправлений админ панели
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext

from app.handlers.admin_settings import (
    admin_ui_photo_settings_menu, admin_setting_handler, process_setting_value,
    process_referral_username, process_referral_percent,
    process_ticket_username, process_ticket_amount,
    AdminSettingStates
)
from app.database.models import get_admin_setting, update_admin_setting


class TestAdminPanelFixes:
    """Тесты для проверки исправлений админ панели"""

    @pytest.fixture
    def mock_callback(self):
        """Создает мок callback query"""
        callback = AsyncMock()
        callback.from_user = types.User(id=123456789, is_bot=False, first_name="Admin")
        callback.message = AsyncMock()
        callback.data = "test_data"
        callback.answer = AsyncMock()
        return callback

    @pytest.fixture
    def mock_message(self):
        """Создает мок сообщения"""
        message = AsyncMock()
        message.from_user = types.User(id=123456789, is_bot=False, first_name="Admin")
        message.text = "test_text"
        message.photo = None
        message.answer = AsyncMock()
        return message

    @pytest.fixture
    def mock_state(self):
        """Создает мок FSM состояния"""
        state = AsyncMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={})
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()
        state.clear = AsyncMock()
        return state

    @patch('app.handlers.admin_settings.is_admin', return_value=True)
    @pytest.mark.asyncio
    async def test_photo_settings_menu(self, mock_is_admin, mock_callback):
        """Тест меню настроек фото"""
        await admin_ui_photo_settings_menu(mock_callback)
        
        # Проверяем, что сообщение было отправлено
        mock_callback.message.answer.assert_called_once()
        
        # Проверяем, что в сообщении есть кнопки для фото
        call_args = mock_callback.message.answer.call_args
        assert "Настройки фото" in call_args[0][0]
        
        # Проверяем наличие кнопок для разных типов фото
        keyboard = call_args[1]['reply_markup']
        button_texts = []
        for row in keyboard.inline_keyboard:
            for button in row:
                button_texts.append(button.callback_data)
        
        expected_callbacks = [
            "admin_setting_main_photo",
            "admin_setting_premium_photo", 
            "admin_setting_stars_photo",
            "admin_setting_reviews_photo",
            "admin_setting_crypto_photo",
            "admin_setting_about_photo",
            "admin_setting_support_photo",
            "admin_setting_profile_photo",
            "admin_setting_slot_photo",
            "admin_setting_calendar_photo"
        ]
        
        for expected in expected_callbacks:
            assert expected in button_texts

    @patch('app.handlers.admin_settings.is_admin', return_value=True)
    @patch('app.handlers.admin_settings.get_setting_with_default')
    @pytest.mark.asyncio
    async def test_photo_setting_handler(self, mock_get_setting, mock_is_admin, mock_callback, mock_state):
        """Тест обработчика настроек фото"""
        mock_callback.data = "admin_setting_stars_photo"
        mock_get_setting.return_value = "https://example.com/photo.jpg"
        
        await admin_setting_handler(mock_callback, mock_state)
        
        # Проверяем, что состояние было установлено
        mock_state.set_state.assert_called_once_with(AdminSettingStates.waiting_for_value)
        
        # Проверяем, что данные были сохранены
        mock_state.update_data.assert_any_call(setting_key="stars_photo")
        mock_state.update_data.assert_any_call(prev_menu="admin_ui_photo_settings")

    @patch('app.handlers.admin_settings.is_admin', return_value=True)
    @patch('app.handlers.admin_settings.update_admin_setting')
    @pytest.mark.asyncio
    async def test_photo_upload_processing(self, mock_update_setting, mock_is_admin, mock_message, mock_state):
        """Тест обработки загрузки фото"""
        # Настраиваем мок для фото
        mock_photo = MagicMock()
        mock_photo.file_id = "BAADBAADrwADBREAAYag2eLPCAABHwI"
        mock_message.photo = [mock_photo]
        mock_message.text = None
        
        # Настраиваем состояние
        mock_state.get_data.return_value = {
            'setting_key': 'stars_photo',
            'prev_menu': 'admin_ui_photo_settings'
        }
        
        await process_setting_value(mock_message, mock_state)
        
        # Проверяем, что настройка была обновлена
        mock_update_setting.assert_called_once_with('stars_photo', mock_photo.file_id)
        
        # Проверяем, что состояние было очищено
        mock_state.clear.assert_called_once()

    @patch('app.handlers.admin_settings.is_admin', return_value=True)
    @patch('app.handlers.admin_settings.get_user_by_username')
    @pytest.mark.asyncio
    async def test_referral_username_processing(self, mock_get_user, mock_is_admin, mock_message, mock_state):
        """Тест обработки юзернейма для рефералов"""
        mock_message.text = "testuser"
        mock_get_user.return_value = {
            'id': 123,
            'tg_id': 123456789,
            'username': 'testuser',
            'full_name': 'Test User',
            'referral_percent': 5.0
        }

        await process_referral_username(mock_message, mock_state)

        # Проверяем, что пользователь был найден
        mock_get_user.assert_called_once_with("testuser")

        # Проверяем, что данные были сохранены
        mock_state.update_data.assert_called()

    @patch('app.handlers.admin_settings.is_admin', return_value=True)
    @patch('app.handlers.admin_settings.update_user_referral_percent_by_username')
    @pytest.mark.asyncio
    async def test_referral_percent_processing(self, mock_update_percent, mock_is_admin, mock_message, mock_state):
        """Тест обработки процента рефералов"""
        mock_message.text = "15.5"
        mock_state.get_data.return_value = {'user_username': 'testuser'}
        mock_update_percent.return_value = True

        await process_referral_percent(mock_message, mock_state)

        # Проверяем, что процент был обновлен
        mock_update_percent.assert_called_once_with('testuser', 15.5)

        # Проверяем, что данные состояния были обновлены (но состояние не очищено)
        mock_state.update_data.assert_called_with(current_percent=15.5)

    @patch('app.handlers.admin_settings.is_admin', return_value=True)
    @patch('app.handlers.admin_settings.get_user_by_username')
    @pytest.mark.asyncio
    async def test_ticket_username_processing(self, mock_get_user, mock_is_admin, mock_message, mock_state):
        """Тест обработки юзернейма для билетиков"""
        mock_message.text = "testuser"
        mock_get_user.return_value = {
            'id': 123,
            'tg_id': 123456789,
            'username': 'testuser',
            'full_name': 'Test User',
            'referral_percent': 5.0
        }

        await process_ticket_username(mock_message, mock_state)

        # Проверяем, что пользователь был найден
        mock_get_user.assert_called_once_with("testuser")

        # Проверяем, что данные были сохранены
        mock_state.update_data.assert_called()

    @patch('app.handlers.admin_settings.is_admin', return_value=True)
    @patch('app.handlers.admin_settings.add_slot_attempts')
    @pytest.mark.asyncio
    async def test_ticket_amount_processing(self, mock_add_attempts, mock_is_admin, mock_message, mock_state):
        """Тест обработки количества билетиков"""
        mock_message.text = "5"
        mock_state.get_data.return_value = {
            'ticket_user_id': 123,
            'ticket_username': 'testuser'
        }
        mock_add_attempts.return_value = True
        
        await process_ticket_amount(mock_message, mock_state)
        
        # Проверяем, что билетики были добавлены
        mock_add_attempts.assert_called_once_with(123, 5)
        
        # Проверяем, что состояние было очищено
        mock_state.clear.assert_called_once()

    @patch('app.handlers.admin_settings.is_admin', return_value=True)
    @pytest.mark.asyncio
    async def test_invalid_text_handling(self, mock_is_admin, mock_state):
        """Тест обработки сообщений без текста"""
        # Создаем сообщение без текста
        message = AsyncMock()
        message.from_user = types.User(id=123456789, is_bot=False, first_name="Admin")
        message.text = None
        message.answer = AsyncMock()
        
        # Тестируем обработчик рефералов
        await process_referral_username(message, mock_state)
        message.answer.assert_called_with("❌ Отправьте текстовое сообщение с юзернеймом")
        
        # Тестируем обработчик билетиков
        await process_ticket_username(message, mock_state)
        message.answer.assert_called_with("❌ Отправьте текстовое сообщение с юзернеймом")

    @patch('app.handlers.admin_settings.is_admin', return_value=True)
    @patch('app.handlers.admin_settings.update_admin_setting')
    @pytest.mark.asyncio
    async def test_photo_upload_flow(self, mock_update_setting, mock_is_admin, mock_state):
        """Тест полного потока загрузки фото"""
        # Настраиваем состояние
        mock_state.get_data.return_value = {
            'setting_key': 'main_photo',
            'prev_menu': 'admin_ui_photo_settings'
        }

        # Создаем сообщение с фото
        message = AsyncMock()
        message.from_user = types.User(id=123456789, is_bot=False, first_name="Admin")
        message.photo = [
            types.PhotoSize(file_id="small_photo", file_unique_id="small", width=100, height=100, file_size=1000),
            types.PhotoSize(file_id="large_photo", file_unique_id="large", width=800, height=600, file_size=50000)
        ]
        message.text = None
        message.answer = AsyncMock()

        # Тестируем обработку фото
        await process_setting_value(message, mock_state)

        # Проверяем, что фото было сохранено (берется самое большое)
        mock_update_setting.assert_called_once_with('main_photo', 'large_photo')

        # Проверяем, что состояние очищено
        mock_state.clear.assert_called_once()

        # Проверяем успешное сообщение
        message.answer.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
