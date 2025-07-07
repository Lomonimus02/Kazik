#!/usr/bin/env python3
"""
Тест исправленной функции удаления пользователя
"""
import sys
import os
import sqlite3
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.models import (
    get_or_create_user, get_user_profile, delete_user_everywhere_full,
    create_order, update_balance
)

def test_user_deletion():
    """Тестирует функцию удаления пользователя"""
    print("🧪 ТЕСТ УДАЛЕНИЯ ПОЛЬЗОВАТЕЛЯ")
    print("=" * 60)
    
    try:
        # Создаем тестового пользователя
        test_tg_id = 999999999
        test_username = "test_user_delete"
        test_full_name = "Test User Delete"
        test_reg_date = "2025-07-07"
        
        print(f"\n1. Создание тестового пользователя {test_tg_id}...")
        user = get_or_create_user(test_tg_id, test_full_name, test_username, test_reg_date)
        print(f"   Пользователь создан: {user}")
        
        # Добавляем баланс
        print("\n2. Добавление баланса...")
        update_balance(test_tg_id, 100.0)
        
        # Создаем заказ
        print("\n3. Создание тестового заказа...")
        create_order(test_tg_id, "telegram_premium", 100.0, "pending")
        
        # Проверяем, что пользователь существует
        print("\n4. Проверка существования пользователя...")
        profile = get_user_profile(test_tg_id)
        if profile:
            print(f"   Профиль найден: {profile['username']}, баланс: {profile['balance']}")
        else:
            print("   ❌ Профиль не найден")
            return
        
        # Проверяем связанные данные в БД
        print("\n5. Проверка связанных данных в БД...")
        conn = sqlite3.connect('data/users.db')
        cursor = conn.cursor()
        
        # Получаем user_id
        cursor.execute('SELECT id FROM users WHERE tg_id=?', (test_tg_id,))
        user_row = cursor.fetchone()
        if user_row:
            user_id = user_row[0]
            print(f"   User ID: {user_id}")
            
            # Проверяем заказы
            cursor.execute('SELECT COUNT(*) FROM orders WHERE user_id=?', (user_id,))
            orders_count = cursor.fetchone()[0]
            print(f"   Заказов: {orders_count}")
        
        conn.close()
        
        # Удаляем пользователя
        print(f"\n6. Удаление пользователя {test_tg_id}...")
        delete_user_everywhere_full(test_tg_id)
        print("   Функция удаления выполнена")
        
        # Проверяем, что пользователь удален
        print("\n7. Проверка удаления...")
        profile_after = get_user_profile(test_tg_id)
        if profile_after:
            print("   ❌ Пользователь все еще существует!")
        else:
            print("   ✅ Пользователь успешно удален")
        
        # Проверяем связанные данные
        print("\n8. Проверка удаления связанных данных...")
        conn = sqlite3.connect('data/users.db')
        cursor = conn.cursor()
        
        # Проверяем заказы
        cursor.execute('SELECT COUNT(*) FROM orders WHERE user_id=?', (user_id,))
        orders_after = cursor.fetchone()[0]
        print(f"   Заказов после удаления: {orders_after}")
        
        # Проверяем основную таблицу пользователей
        cursor.execute('SELECT COUNT(*) FROM users WHERE tg_id=?', (test_tg_id,))
        users_after = cursor.fetchone()[0]
        print(f"   Записей пользователя: {users_after}")
        
        conn.close()
        
        if orders_after == 0 and users_after == 0:
            print("\n✅ Тест удаления пользователя ПРОЙДЕН!")
        else:
            print("\n❌ Тест удаления пользователя ПРОВАЛЕН!")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_user_deletion()
