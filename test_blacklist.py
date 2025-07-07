#!/usr/bin/env python3
"""
Тест системы черного списка
"""
import asyncio
import aiosqlite
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.handlers.user import is_blacklisted, add_to_blacklist, remove_from_blacklist

async def test_blacklist():
    """Тестирует функции черного списка"""
    test_user_id = 123456789
    test_reason = "Тестовая причина"
    
    print("🧪 Тестирование системы черного списка...")
    
    # 1. Проверяем, что пользователь не в ЧС
    result = await is_blacklisted(test_user_id)
    print(f"1. Пользователь {test_user_id} в ЧС: {result}")
    assert result is None, "Пользователь не должен быть в ЧС изначально"
    
    # 2. Добавляем в ЧС
    await add_to_blacklist(test_user_id, test_reason)
    print(f"2. Добавили пользователя {test_user_id} в ЧС с причиной: {test_reason}")
    
    # 3. Проверяем, что пользователь теперь в ЧС
    result = await is_blacklisted(test_user_id)
    print(f"3. Пользователь {test_user_id} в ЧС: {result}")
    assert result == test_reason, f"Ожидали '{test_reason}', получили '{result}'"
    
    # 4. Удаляем из ЧС
    await remove_from_blacklist(test_user_id)
    print(f"4. Удалили пользователя {test_user_id} из ЧС")
    
    # 5. Проверяем, что пользователь больше не в ЧС
    result = await is_blacklisted(test_user_id)
    print(f"5. Пользователь {test_user_id} в ЧС: {result}")
    assert result is None, "Пользователь должен быть удален из ЧС"
    
    print("✅ Все тесты черного списка прошли успешно!")

async def test_blacklist_database():
    """Тестирует структуру базы данных черного списка"""
    print("\n🗄️ Тестирование базы данных черного списка...")
    
    async with aiosqlite.connect('data/blacklist.db') as db:
        # Проверяем структуру таблицы
        cursor = await db.execute("PRAGMA table_info(blacklist)")
        columns = await cursor.fetchall()
        
        expected_columns = ['tg_id', 'reason', 'date_added']
        actual_columns = [col[1] for col in columns]
        
        print(f"Столбцы в таблице blacklist: {actual_columns}")
        
        for col in expected_columns:
            assert col in actual_columns, f"Отсутствует столбец: {col}"
        
        print("✅ Структура базы данных корректна!")

async def main():
    """Главная функция тестирования"""
    try:
        await test_blacklist()
        await test_blacklist_database()
        print("\n🎉 Все тесты системы черного списка прошли успешно!")
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        return 1
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
