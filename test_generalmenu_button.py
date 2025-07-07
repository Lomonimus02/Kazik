#!/usr/bin/env python3
"""
Тест для проверки работы кнопки generalmenu в рассылке
"""
import asyncio
import logging
import sys
import os

# Добавляем путь к проекту
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
os.chdir(current_dir)

from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.config import BOT_TOKEN, ADMINS
from app.database.models import get_admin_setting

# Настройка логирования
logging.basicConfig(level=logging.INFO)

async def test_generalmenu_button():
    """Тестирует работу кнопки generalmenu"""
    try:
        bot = Bot(token=BOT_TOKEN)
        
        # Создаем тестовую рассылку с кнопкой generalmenu
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="generalmenu")],
            [InlineKeyboardButton(text="⭐ Звезды", callback_data="buystars")],
            [InlineKeyboardButton(text="🎰 Слот-машина", callback_data="slot_machine")]
        ])
        
        # Отправляем тестовое сообщение первому админу
        admin_id = ADMINS[0] if ADMINS else None
        if not admin_id:
            print("❌ Нет админов для тестирования")
            return False
            
        message_text = (
            "🧪 <b>ТЕСТ КНОПКИ GENERALMENU</b>\n\n"
            "Это тестовое сообщение для проверки работы кнопки 'Главное меню' в рассылке.\n\n"
            "Нажмите на кнопку 'Главное меню' ниже - она должна открыть главное меню "
            "БЕЗ удаления этого сообщения."
        )
        
        await bot.send_message(
            chat_id=admin_id,
            text=message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        print(f"✅ Тестовое сообщение отправлено админу {admin_id}")
        print("📝 Проверьте:")
        print("   1. Нажмите кнопку 'Главное меню'")
        print("   2. Должно открыться главное меню")
        print("   3. Сообщение рассылки НЕ должно удалиться")
        
        await bot.session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_generalmenu_button())
    if success:
        print("\n🎉 Тест отправлен успешно!")
    else:
        print("\n💥 Тест не удался!")
        sys.exit(1)
