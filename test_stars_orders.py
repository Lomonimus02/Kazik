#!/usr/bin/env python3
"""
Тест исправления бага подтверждения заказов звезд
"""
import asyncio
import os
import sys
import json
import datetime

# Добавляем путь к проекту
sys.path.insert(0, os.path.abspath('.'))

from app.database.models import (
    get_or_create_user, get_user_profile, create_order, 
    get_order_by_id, update_order_status, get_user_profile_by_id
)

def test_stars_order_system():
    """Тестирует систему заказов звезд"""
    print("🧪 Тестирование системы заказов звезд...")
    
    try:
        # Тест 1: Создание тестового пользователя
        print("\n1️⃣ Создание тестового пользователя...")
        
        test_tg_id = 999003
        test_name = "Тест Пользователь Звезды"
        test_username = "test_stars_user"
        reg_date = "2024-01-01"
        
        get_or_create_user(test_tg_id, test_name, test_username, reg_date, None)
        user_profile = get_user_profile(test_tg_id)
        print(f"✅ Создан пользователь: {user_profile['full_name']} (DB ID: {user_profile['id']})")
        
        # Тест 2: Создание заказа звезд
        print("\n2️⃣ Создание заказа звезд...")
        
        order_id = create_order(
            user_id=user_profile['id'],  # Используем database ID
            order_type="stars",
            amount=100.0,  # Цена в рублях
            status="pending",
            file_id="test_file_id",
            extra_data={
                "amount": 50,  # Количество звезд
                "recipient": "@test_stars_user"
            }
        )
        
        print(f"✅ Создан заказ звезд: ID {order_id}")
        
        # Тест 3: Получение заказа
        print("\n3️⃣ Проверка созданного заказа...")
        
        order = get_order_by_id(order_id)
        if order:
            print(f"✅ Заказ найден:")
            print(f"   - ID: {order['id']}")
            print(f"   - Пользователь (DB ID): {order['user_id']}")
            print(f"   - Тип: {order['order_type']}")
            print(f"   - Сумма: {order['amount']}₽")
            print(f"   - Статус: {order['status']}")
            
            # Проверяем extra_data
            if order['extra_data']:
                extra_data = json.loads(order['extra_data'])
                print(f"   - Количество звезд: {extra_data.get('amount', 'не указано')}")
                print(f"   - Получатель: {extra_data.get('recipient', 'не указан')}")
        else:
            print("❌ Заказ не найден!")
            return False
        
        # Тест 4: Обновление статуса заказа (имитация подтверждения админом)
        print("\n4️⃣ Тест подтверждения заказа...")
        
        confirm_time = datetime.datetime.now().strftime('%H:%M %d.%m.%Y')
        extra_data_update = {
            **json.loads(order['extra_data'] if order['extra_data'] else '{}'),
            "confirmed_at": confirm_time,
            "confirmed_by": "@test_admin"
        }
        
        success = update_order_status(
            order_id=order_id,
            status="completed",
            extra_data=extra_data_update
        )
        
        if success:
            print(f"✅ Заказ успешно подтвержден")
            
            # Проверяем обновленный заказ
            updated_order = get_order_by_id(order_id)
            if updated_order:
                print(f"✅ Статус обновлен: {updated_order['status']}")
                if updated_order['extra_data']:
                    updated_extra = json.loads(updated_order['extra_data'])
                    print(f"✅ Время подтверждения: {updated_extra.get('confirmed_at', 'не указано')}")
                    print(f"✅ Подтвердил: {updated_extra.get('confirmed_by', 'не указано')}")
        else:
            print("❌ Ошибка при подтверждении заказа!")
            return False
        
        # Тест 5: Проверка получения профиля пользователя по database ID
        print("\n5️⃣ Тест получения профиля пользователя...")
        
        user_profile_by_id = get_user_profile_by_id(user_profile['id'])
        if user_profile_by_id:
            print(f"✅ Профиль найден по DB ID:")
            print(f"   - Telegram ID: {user_profile_by_id['tg_id']}")
            print(f"   - Имя: {user_profile_by_id['full_name']}")
            print(f"   - Username: {user_profile_by_id['username']}")
        else:
            print("❌ Профиль пользователя не найден!")
            return False
        
        # Тест 6: Тест отклонения заказа
        print("\n6️⃣ Создание и отклонение заказа...")
        
        # Создаем второй заказ для теста отклонения
        order_id_2 = create_order(
            user_id=user_profile['id'],
            order_type="stars",
            amount=200.0,
            status="pending",
            file_id="test_file_id_2",
            extra_data={
                "amount": 100,
                "recipient": "@test_stars_user"
            }
        )
        
        # Отклоняем заказ
        reject_time = datetime.datetime.now().strftime('%H:%M %d.%m.%Y')
        reject_extra_data = {
            **json.loads(get_order_by_id(order_id_2)['extra_data'] if get_order_by_id(order_id_2)['extra_data'] else '{}'),
            "rejected_at": reject_time,
            "rejected_by": "@test_admin"
        }
        
        success_reject = update_order_status(
            order_id=order_id_2,
            status="rejected",
            extra_data=reject_extra_data
        )
        
        if success_reject:
            print(f"✅ Заказ #{order_id_2} успешно отклонен")
            rejected_order = get_order_by_id(order_id_2)
            if rejected_order and rejected_order['status'] == 'rejected':
                print(f"✅ Статус корректно обновлен: {rejected_order['status']}")
        else:
            print("❌ Ошибка при отклонении заказа!")
            return False
        
        print("\n🎉 Все тесты системы заказов звезд прошли успешно!")
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = test_stars_order_system()
    if result:
        print("\n✅ Система заказов звезд работает корректно!")
    else:
        print("\n❌ Обнаружены проблемы в системе заказов звезд!")
        sys.exit(1)
